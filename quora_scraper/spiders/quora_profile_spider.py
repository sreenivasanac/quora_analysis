import scrapy
import time
import logging
import signal
import sys
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from ..items import QuoraAnswerItem
from quora_scraper.database import database_context
from quora_scraper.chrome_driver_manager import get_chrome_manager

logger = logging.getLogger(__name__)


class QuoraProfileSpider(scrapy.Spider):
    """Spider to extract all answers from Kanthaswamy Balasubramaniam's Quora profile"""
    
    name = 'Kanthaswamy Balasubramaniam Profile Spider'
    allowed_domains = ['quora.com']
    start_urls = ['https://www.quora.com/profile/Kanthaswamy-Balasubramaniam/answers']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 2,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 0.3,
        'AUTOTHROTTLE_MAX_DELAY': 1,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chrome_manager = get_chrome_manager()
        self.seen_answer_urls = set()
        self.database_saved_urls = set()  # URLs already in database
        self.unsaved_links = set()  # Links collected but not yet saved to database
        self.answers_found = 0
        self.scroll_count = 0
        self.no_new_answers_count = 0

        # Load existing URLs from database at startup
        self.load_existing_urls_from_database()

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        
    def graceful_shutdown(self, signum, frame):
        """Handle graceful shutdown on Ctrl+C"""
        print("\n\n" + "="*70)
        print("GRACEFUL SHUTDOWN INITIATED")
        print("="*70)

        if self.unsaved_links:
            print(f"Saving {len(self.unsaved_links)} unsaved links to database...")
            self.save_batch_to_database(list(self.unsaved_links))
            self.unsaved_links.clear()
            print(f"✓ Links saved successfully")
        else:
            print("No unsaved links to save")

        print(f"\nTotal links in database: {len(self.database_saved_urls)}")
        print("="*70)

        # Clean up Chrome driver
        if self.chrome_manager:
            self.chrome_manager.cleanup()

        sys.exit(0)

    def load_existing_urls_from_database(self):
        """Load all existing answered_question_url from database to avoid duplicates"""

        logger.info("Loading existing URLs from database...")

        try:
            # Use context manager for database operations
            with database_context() as db:
                # Get all existing URLs
                self.database_saved_urls = db.get_all_answer_urls()

        except Exception as e:
            logger.error(f"Error loading existing URLs from database: {e}")
            logger.warning("Continuing without existing URL filtering...")
            self.database_saved_urls = set()  # Empty set if database read fails
    
    async def start(self):
        """Generate the initial request using the new async start method"""
        # Instead of making HTTP requests, we'll use the authenticated Selenium driver
        # The middleware will handle authentication, then we'll use that driver directly
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_with_selenium,  # Changed callback
            dont_filter=True,
            meta={'use_selenium': True}  # Flag to indicate we want to use Selenium
        )

    def start_requests(self):
        """Maintain backward compatibility with older Scrapy versions"""
        # Call the parent start_requests to use the new start() method
        return super().start_requests()
    
    def parse_with_selenium(self, response):
        """Parse answers page with resumable scrolling"""

        logger.info(f"Starting to process {response.url}")
        logger.info(f"Database contains {len(self.database_saved_urls)} existing URLs to skip")

        # Setup Chrome driver first
        if not self.chrome_manager.setup_driver():
            logger.error("Failed to setup Chrome driver")
            return

        # Now check authentication with the properly set up driver
        if not self.chrome_manager.is_authenticated():
            logger.error("Not authenticated to Quora. Please login in the browser first to authenticate.")
            return

        # Check if we're already on the profile page (for resume capability)
        try:
            current_url = self.chrome_manager.get_driver().current_url
            logger.info(f"Current browser URL: {current_url}")

            # Check if we're already on the target profile page
            if "Kanthaswamy-Balasubramaniam/answers" in current_url:
                logger.info("✓ Already on profile page, resuming from current position")
                # Give page a moment to stabilize
                time.sleep(2)
            else:
                logger.info("Navigating to profile page...")
                self.chrome_manager.get_driver().get(response.url)
                time.sleep(5)  # Wait for initial page load
        except Exception as e:
            logger.warning(f"Could not check current URL, navigating to target: {e}")
            self.chrome_manager.get_driver().get(response.url)
            time.sleep(5)
        
        # Collect all answer links by scrolling until complete
        all_answer_links = self.scroll_until_complete()
        
        # Since we're now using batched saving during collection,
        # we mainly need to handle any final statistics
        total_found = len(all_answer_links)
        total_existing = len([link for link in all_answer_links if link in self.database_saved_urls])
        new_found = total_found - total_existing

        logger.info(f"COLLECTION SUMMARY:")
        logger.info(f"  Total links found: {total_found}")
        logger.info(f"  Already in database: {total_existing}")
        logger.info(f"  New links collected: {new_found}")

        # Update our counter for the spider statistics
        self.answers_found = new_found

        # Note: URLs are already saved to database via batched operations
        # No need to yield items since we've bypassed the pipeline for efficiency
        
        logger.info(f"Total new answers found in this session: {self.answers_found}")
        
        # Clean up driver
        self.chrome_manager.cleanup()
        
    def scroll_until_complete(self):
        """Scroll through the page until all content is loaded with proper batched saving"""
        logger.info("Starting comprehensive scrolling to collect all answer links")

        # Track all links seen and links not yet saved
        all_links = set()
        self.unsaved_links.clear()  # Clear any previous unsaved links

        # First, extract any links already visible on the page (for resume capability)
        initial_links = self.extract_answer_links_from_selenium()
        logger.info(f"Found {len(initial_links)} links already visible on page")

        # Add initial links and track unsaved ones
        for link in initial_links:
            all_links.add(link)
            if link not in self.database_saved_urls:
                self.unsaved_links.add(link)

        logger.info(f"Starting with {len(self.unsaved_links)} unsaved links from current view")

        start_time = time.time()
        last_height = self.chrome_manager.get_driver().execute_script("return document.body.scrollHeight")

        # Enhanced end-detection counters
        scroll_attempts_without_new_content = 0
        attempts_without_new_links = 0
        total_scroll_attempts = 0
        batch_size = 200
        last_checkpoint_time = time.time()
        total_saved_this_session = 0

        while True:
            # Get current answer links
            current_links = self.extract_answer_links_from_selenium()
            links_before = len(all_links)

            # Track new links found in this scroll
            new_links_this_scroll = []
            for link in current_links:
                if link not in all_links:
                    all_links.add(link)
                    # Check if it's truly new (not in database)
                    if link not in self.database_saved_urls:
                        self.unsaved_links.add(link)
                        new_links_this_scroll.append(link)

            new_links_found = len(all_links) - links_before

            total_scroll_attempts += 1
            elapsed_time = int(time.time() - start_time)

            # FIXED: Save batch when we have enough UNSAVED links
            if len(self.unsaved_links) >= batch_size:
                links_to_save = list(self.unsaved_links)
                logger.info(f"Saving batch of {len(links_to_save)} unsaved links...")
                saved_count = self.save_batch_to_database(links_to_save)
                if saved_count > 0:
                    # Update our tracking
                    self.database_saved_urls.update(links_to_save)
                    self.unsaved_links.clear()
                    total_saved_this_session += saved_count
                    print()  # New line for batch save notification
                    logger.info(f"✓ Batch saved: {saved_count} links (Total saved this session: {total_saved_this_session})")

            # Log progress every 20 attempts or when new links found
            if total_scroll_attempts % 20 == 0 or new_links_found > 0:
                rate = len(all_links) / elapsed_time if elapsed_time > 0 else 0
                status = f"Scroll {total_scroll_attempts} (t={elapsed_time}s): Total: {len(all_links)} | Unsaved: {len(self.unsaved_links)} | Saved: {total_saved_this_session} | Rate: {rate:.1f}/s"
                print(f"\r{status}", end="", flush=True)

            # Checkpoint logging every 5 minutes
            if time.time() - last_checkpoint_time >= 300:
                print()  # New line before checkpoint
                logger.info(f"CHECKPOINT: {len(all_links)} total links collected in {elapsed_time}s")
                last_checkpoint_time = time.time()

            # Update counters for end-detection
            if new_links_found == 0:
                attempts_without_new_links += 1
            else:
                attempts_without_new_links = 0

            # Scroll down to bottom
            self.chrome_manager.get_driver().execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for content to load (adaptive timing)
            time.sleep(1.5 if total_scroll_attempts < 50 else 1)

            # Calculate new scroll height
            new_height = self.chrome_manager.get_driver().execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                scroll_attempts_without_new_content += 1
            else:
                scroll_attempts_without_new_content = 0
                last_height = new_height

            # Enhanced end-detection: Stop when multiple indicators suggest completion
            if (scroll_attempts_without_new_content >= 30 and
                attempts_without_new_links >= 50):
                print()  # New line before end detection
                logger.info(f"End of content detected: {scroll_attempts_without_new_content} height attempts, {attempts_without_new_links} link attempts")
                break

        # Save any remaining unsaved links
        if self.unsaved_links:
            print()  # New line before saving
            logger.info(f"Saving {len(self.unsaved_links)} remaining unsaved links...")
            saved_count = self.save_final_batch_to_database(list(self.unsaved_links))
            if saved_count > 0:
                self.database_saved_urls.update(self.unsaved_links)
                total_saved_this_session += saved_count
                self.unsaved_links.clear()

        final_elapsed = int(time.time() - start_time)
        print()  # New line before completion
        logger.info(f"Completed scrolling after {final_elapsed}s")
        logger.info(f"Total unique links found: {len(all_links)}")
        logger.info(f"Links saved this session: {total_saved_this_session}")
        logger.info(f"Total links in database: {len(self.database_saved_urls)}")
        return list(all_links)

    def save_batch_to_database(self, batch_urls):
        """Save a batch of URLs to database and return count of saved URLs"""
        try:
            # No need to filter here since we're tracking unsaved links properly now
            if batch_urls:
                with database_context() as db:
                    inserted_count = db.insert_answer_links_batch(batch_urls)
                    return inserted_count
            return 0
        except Exception as e:
            logger.error(f"Error saving batch: {e}")
            return 0

    def save_final_batch_to_database(self, final_urls):
        """Save final batch and return count for statistics"""
        try:
            if final_urls:
                with database_context() as db:
                    inserted_count = db.insert_answer_links_batch(final_urls)
                    logger.info(f"Final batch saved: {inserted_count} new URLs inserted")
                    return inserted_count
            return 0
        except Exception as e:
            logger.error(f"Error saving final batch: {e}")
            return 0

    def extract_answer_links_from_selenium(self):
        """Extract answer links from current page state using Selenium with fallback selectors"""
        try:
            links = []

            # Primary selector
            elements = self.chrome_manager.get_driver().find_elements(By.CSS_SELECTOR, "a.answer_timestamp")
            for element in elements:
                href = element.get_attribute('href')
                if href and '/answer/' in href:
                    links.append(href)

            # Fallback selectors if primary doesn't work well
            if len(links) < 10:  # If we found very few links, try alternatives
                fallback_selectors = [
                    "a[href*='/answer/']",
                    ".answer_content_wrapper a[href*='/answer/']",
                    "[class*='answer'] a[href*='/answer/']"
                ]

                for selector in fallback_selectors:
                    try:
                        fallback_elements = self.chrome_manager.get_driver().find_elements(By.CSS_SELECTOR, selector)
                        for element in fallback_elements:
                            href = element.get_attribute('href')
                            if href and '/answer/' in href and href not in links:
                                links.append(href)
                    except:
                        continue

            return links

        except Exception as e:
            logger.error(f"Error extracting links with Selenium: {e}")
            return []
    
    def closed(self, reason):
        """Called when the spider closes"""
        # Ensure driver is cleaned up
        self.chrome_manager.cleanup()
        
        logger.info(f"Spider closed. Reason: {reason}")
        logger.info(f"New answers found in this session: {self.answers_found}")
        logger.info(f"Total URLs in database (before this session): {len(self.database_saved_urls)}")
        logger.info(f"Total URLs in database (after this session): {len(self.database_saved_urls) + self.answers_found}")
        
        if self.answers_found == 0:
            logger.info("No new answers found - all URLs may already be in database")
        else:
            logger.info(f"Successfully collected {self.answers_found} new answers!")

 