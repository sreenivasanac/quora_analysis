import scrapy
import time
import logging
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
        self.answers_found = 0
        self.scroll_count = 0
        self.no_new_answers_count = 0

        # Load existing URLs from database at startup
        self.load_existing_urls_from_database()
        
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
    
    def start_requests(self):
        """Generate the initial request using the standard Scrapy start_requests method"""
        # Instead of making HTTP requests, we'll use the authenticated Selenium driver
        # The middleware will handle authentication, then we'll use that driver directly
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_with_selenium,  # Changed callback
            dont_filter=True,
            meta={'use_selenium': True}  # Flag to indicate we want to use Selenium
        )
    
    def parse_with_selenium(self, response):
        """Parse answers page with 300-second scrolling to load all content"""

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
        
        # Load the page in Selenium
        self.chrome_manager.get_driver().get(response.url)
        time.sleep(5)  # Wait for initial page load
        
        # Scroll for 300 seconds and collect all answer links
        number_of_seconds_to_scroll = 300 # len(self.database_saved_urls)
        all_answer_links = self.scroll_for_duration(number_of_seconds_to_scroll)  # 300 seconds = 5 minutes
        import pdb; pdb.set_trace()
        
        # Filter out URLs that already exist in database
        new_urls = []
        skipped_urls = 0
        
        for link in all_answer_links:
            if link:
                # Ensure the link is absolute
                absolute_url = urljoin(response.url, link)
                
                # Check if URL already exists in database
                if absolute_url in self.database_saved_urls:
                    skipped_urls += 1
                    continue
                
                # Check if we've already seen this URL in current session
                if absolute_url not in self.seen_answer_urls:
                    self.seen_answer_urls.add(absolute_url)
                    new_urls.append(absolute_url)
        
        logger.info(f"Found {len(all_answer_links)} total links")
        logger.info(f"Skipped {skipped_urls} URLs already in database")
        logger.info(f"Found {len(new_urls)} new URLs to save")
        
        # Yield items for new URLs only
        for url in new_urls:
            item = QuoraAnswerItem()
            item['answered_question_url'] = url
            yield item
            self.answers_found += 1
        
        logger.info(f"Total new answers found in this session: {self.answers_found}")
        
        # Clean up driver
        self.chrome_manager.cleanup()
        
    def scroll_for_duration(self, duration_seconds):
        """Scroll through the page for a specified duration and collect all answer links"""
        logger.info(f"Starting {duration_seconds}-second scrolling to load all content")
        
        all_links = set()
        start_time = time.time()
        last_height = self.chrome_manager.get_driver().execute_script("return document.body.scrollHeight")
        scroll_attempts_without_new_content = 0
        total_scroll_attempts = 0
        
        while time.time() - start_time < duration_seconds:
            # Get current answer links
            current_links = self.extract_answer_links_from_selenium()
            links_before = len(all_links)
            all_links.update(current_links)
            new_links_found = len(all_links) - links_before
            
            total_scroll_attempts += 1
            elapsed_time = int(time.time() - start_time)
            
            logger.info(f"Scroll attempt {total_scroll_attempts} (t={elapsed_time}s): Found {len(current_links)} links on page, {new_links_found} new. Total unique: {len(all_links)}")
            
            # Scroll down to bottom
            self.chrome_manager.get_driver().execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(1)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.chrome_manager.get_driver().execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                # No new content loaded
                scroll_attempts_without_new_content += 1
                if scroll_attempts_without_new_content >= 10:  # If no new content for 10 attempts (20 seconds), stop early
                    logger.info(f"No new content loaded after {scroll_attempts_without_new_content} attempts. Stopping early at {elapsed_time}s.")
                    break
            else:
                # New content loaded, reset counter
                scroll_attempts_without_new_content = 0
                last_height = new_height
            
            # Brief pause between scrolls to avoid overwhelming the page
            time.sleep(1)
        
        final_elapsed = int(time.time() - start_time)
        logger.info(f"Finished scrolling after {final_elapsed} seconds. Total unique answer links collected: {len(all_links)}")
        return list(all_links)

    def extract_answer_links_from_selenium(self):
        """Extract answer links from current page state using Selenium"""
        try:
            # Primary selector
            links = []
            
            # Try the primary CSS selector
            elements = self.chrome_manager.get_driver().find_elements(By.CSS_SELECTOR, "a.answer_timestamp")
            for element in elements:
                href = element.get_attribute('href')
                if href:
                    links.append(href)
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

 