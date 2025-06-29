import scrapy
import time
import logging
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from ..items import QuoraAnswerItem
from quora_scraper.database import DatabaseManager
from datetime import datetime
import pytz
from html_to_markdown import convert_to_markdown

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
        self.driver = None
        self.seen_answer_urls = set()
        self.database_saved_urls = set()  # URLs already in database
        self.answers_found = 0
        self.scroll_count = 0
        self.no_new_answers_count = 0
        
        # Check if we should process existing entries
        self.process_mode = kwargs.get('process_mode', 'collect')  # 'collect' or 'process'
        
        if self.process_mode == 'collect':
            # Load existing URLs from database at startup for collection mode
            self.load_existing_urls_from_database()
        else:
            logger.info("Running in process mode - will populate existing database entries")
        
    def load_existing_urls_from_database(self):
        """Load all existing answered_question_url from database to avoid duplicates"""
        
        logger.info("Loading existing URLs from database...")
        
        try:
            # Create DatabaseManager instance and connect
            db_manager = DatabaseManager()
            db_manager.connect()
            
            # Get all existing URLs
            self.database_saved_urls = db_manager.get_all_answer_urls()
            
            # Disconnect
            db_manager.disconnect()
            
        except Exception as e:
            logger.error(f"Error loading existing URLs from database: {e}")
            logger.warning("Continuing without existing URL filtering...")
            self.database_saved_urls = set()  # Empty set if database read fails
    
    def start_requests(self):
        """Generate the initial request"""
        if self.process_mode == 'process':
            # Process existing database entries
            yield scrapy.Request(
                url='https://www.quora.com/',  # Dummy URL for processing mode
                callback=self.process_existing_entries,
                dont_filter=True,
                meta={'use_selenium': True}
            )
        else:
            # Instead of making HTTP requests, we'll use the authenticated Selenium driver
            # The middleware will handle authentication, then we'll use that driver directly
            yield scrapy.Request(
                url=self.start_urls[0],
                callback=self.parse_with_selenium,  # Changed callback
                dont_filter=True,
                meta={'use_selenium': True}  # Flag to indicate we want to use Selenium
            )
    
    def setup_selenium_driver(self):
        """Setup Selenium driver for scrolling"""
        if self.driver is None:
            # Try to get the driver from the middleware first
            if hasattr(self.crawler.engine.downloader, 'middleware') and hasattr(self.crawler.engine.downloader.middleware, 'middlewares'):
                for middleware in self.crawler.engine.downloader.middleware.middlewares:
                    if hasattr(middleware, 'driver') and middleware.driver:
                        self.driver = middleware.driver
                        logger.info("Using shared driver from AuthMiddleware")
                        return
            
            # Fallback: create our own driver if middleware driver not available
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            # Comment out headless for debugging
            # chrome_options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Selenium driver initialized for scrolling")

    def parse_with_selenium(self, response):
        """Parse answers page with 300-second scrolling to load all content"""
        logger.info(f"Starting to process {response.url}")
        logger.info(f"Database contains {len(self.database_saved_urls)} existing URLs to skip")
        
        # Setup Selenium driver if not already done
        self.setup_selenium_driver()
        
        # Load the page in Selenium
        self.driver.get(response.url)
        time.sleep(2)  # Wait for initial page load
        
        # Scroll for 300 seconds and collect all answer links
        all_answer_links = self.scroll_for_duration(20)  # 300 seconds = 5 minutes
        
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
        self.cleanup_driver()
        
    def scroll_for_duration(self, duration_seconds):
        """Scroll through the page for a specified duration and collect all answer links"""
        logger.info(f"Starting {duration_seconds}-second scrolling to load all content")
        
        all_links = set()
        start_time = time.time()
        last_height = self.driver.execute_script("return document.body.scrollHeight")
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
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(1)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
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
            elements = self.driver.find_elements(By.CSS_SELECTOR, "a.answer_timestamp")
            for element in elements:
                href = element.get_attribute('href')
                if href:
                    links.append(href)
            
            # If primary selector doesn't work, try alternatives
            if not links:
                alternative_selectors = [
                    "a[href*='/answer/']",
                    "a[href*='Kanthaswamy-Balasubramaniam/answer/']",
                    ".answer_item a[href*='/answer/']"
                ]
                
                for selector in alternative_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and '/answer/' in href:
                            links.append(href)
                    
                    if links:
                        logger.info(f"Found {len(links)} links using alternative selector: {selector}")
                        break
            
            return links
            
        except Exception as e:
            logger.error(f"Error extracting links with Selenium: {e}")
            return []
    
    def cleanup_driver(self):
        """Clean up Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Selenium driver cleaned up")
    
    def closed(self, reason):
        """Called when the spider closes"""
        # Ensure driver is cleaned up
        self.cleanup_driver()
        
        logger.info(f"Spider closed. Reason: {reason}")
        logger.info(f"New answers found in this session: {self.answers_found}")
        logger.info(f"Total URLs in database (before this session): {len(self.database_saved_urls)}")
        logger.info(f"Total URLs in database (after this session): {len(self.database_saved_urls) + self.answers_found}")
        
        if self.answers_found == 0:
            logger.info("No new answers found - all URLs may already be in database")
        else:
            logger.info(f"Successfully collected {self.answers_found} new answers!")

    def process_existing_entries(self, response):
        """Process existing database entries and populate missing fields"""
        logger.info("Starting to process existing database entries")
        
        # Setup Selenium driver if not already done
        self.setup_selenium_driver()
        
        # Connect to database and get incomplete entries
        db_manager = DatabaseManager()
        db_manager.connect()
        
        try:
            incomplete_entries = db_manager.get_incomplete_entries()
            total_entries = len(incomplete_entries)
            
            if total_entries == 0:
                logger.info("No incomplete entries found in database")
                return
            
            logger.info(f"Found {total_entries} incomplete entries to process")
            
            processed_count = 0
            success_count = 0
            
            for entry in incomplete_entries:
                answered_question_url = entry['answered_question_url']
                entry_id = entry['id']
                
                try:
                    logger.info(f"Processing entry {processed_count + 1}/{total_entries}: {answered_question_url}")
                    
                    # Extract data from the answer page
                    answer_data = self.extract_answer_data(answered_question_url)
                    
                    if answer_data:
                        # Update database with extracted data
                        success = db_manager.update_answer_data(
                            answered_question_url=answered_question_url,
                            question_url=answer_data.get('question_url'),
                            question_text=answer_data.get('question_text'),
                            answer_content=answer_data.get('answer_content'),
                            revision_link=answer_data.get('revision_link'),
                            post_timestamp_raw=answer_data.get('post_timestamp_raw'),
                            post_timestamp_parsed=answer_data.get('post_timestamp_parsed')
                        )
                        
                        if success:
                            success_count += 1
                            logger.info(f"Successfully updated entry {entry_id}")
                        else:
                            logger.error(f"Failed to update database for entry {entry_id}")
                    else:
                        logger.error(f"Failed to extract data for entry {entry_id}")
                    
                    processed_count += 1

                    import pdb; pdb.set_trace()
                    
                    # Log progress every 50 entries
                    if processed_count % 50 == 0:
                        logger.info(f"Progress: {processed_count}/{total_entries} processed, {success_count} successful")
                    
                    # Add delay between requests to be respectful
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing entry {entry_id}: {e}")
                    processed_count += 1
                    continue
            
            logger.info(f"Processing complete: {processed_count} entries processed, {success_count} successful")
            
        finally:
            db_manager.disconnect()
            self.cleanup_driver()
    
    def extract_answer_data(self, answered_question_url: str) -> dict:
        """Extract all required data from an answer page"""
        try:
            # Navigate to the answer page
            self.driver.get(answered_question_url)
            time.sleep(1)  # Wait for page to load
            
            answer_data = {}
            
            # Extract question URL
            try:
                question_url_element = self.driver.find_element(By.CSS_SELECTOR, ".puppeteer_test_question_title a")
                answer_data['question_url'] = question_url_element.get_attribute('href')
            except Exception as e:
                logger.warning(f"Could not extract question URL: {e}")
                answer_data['question_url'] = None
            
            # Extract question text
            try:
                question_text_element = self.driver.find_element(By.CSS_SELECTOR, ".puppeteer_test_question_title a")
                answer_data['question_text'] = question_text_element.text.strip()
            except Exception as e:
                logger.warning(f"Could not extract question text: {e}")
                answer_data['question_text'] = None
            
            # Extract answer content and convert to markdown
            try:
                answer_content_element = self.driver.find_element(By.CSS_SELECTOR, "div.q-text")
                answer_html = answer_content_element.get_attribute('innerHTML')
                
                # Convert HTML to markdown
                answer_markdown = convert_to_markdown(
                    answer_html,
                    heading_style="atx",
                    strong_em_symbol="*",
                    wrap=True,
                    wrap_width=100,
                    escape_asterisks=True
                )
                answer_data['answer_content'] = answer_markdown.strip()
            except Exception as e:
                logger.warning(f"Could not extract answer content: {e}")
                answer_data['answer_content'] = None
            
            # Extract revision data from log page
            log_url = f"{answered_question_url}/log"
            try:
                self.driver.get(log_url)
                time.sleep(1)
                
                # Extract revision link
                try:
                    revision_link_element = self.driver.find_element(By.CSS_SELECTOR, "a.puppeteer_test_link")
                    answer_data['revision_link'] = revision_link_element.get_attribute('href')
                except Exception as e:
                    logger.warning(f"Could not extract revision link: {e}")
                    answer_data['revision_link'] = None
                
                # Extract post timestamp
                try:
                    timestamp_element = self.driver.find_element(By.CSS_SELECTOR, "span.c1h7helg.c8970ew:last-child")
                    timestamp_raw = timestamp_element.text.strip()
                    answer_data['post_timestamp_raw'] = timestamp_raw
                    
                    # Parse timestamp
                    parsed_timestamp = self.parse_quora_timestamp(timestamp_raw)
                    answer_data['post_timestamp_parsed'] = parsed_timestamp
                    
                except Exception as e:
                    logger.warning(f"Could not extract timestamp: {e}")
                    answer_data['post_timestamp_raw'] = None
                    answer_data['post_timestamp_parsed'] = None
                    
            except Exception as e:
                logger.warning(f"Could not access log page {log_url}: {e}")
                answer_data['revision_link'] = None
                answer_data['post_timestamp_raw'] = None
                answer_data['post_timestamp_parsed'] = None
            
            return answer_data
            
        except Exception as e:
            logger.error(f"Failed to extract data from {answered_question_url}: {e}")
            return None
    
    def parse_quora_timestamp(self, timestamp_str: str):
        """Convert Quora timestamp string to datetime object with timezone"""
        if not timestamp_str:
            return None
            
        try:
            # Parse the timestamp string (e.g., "June 27, 2025 at 10:26:56 PM")
            dt = datetime.strptime(timestamp_str, "%B %d, %Y at %I:%M:%S %p")
            
            # Set timezone (assuming Pacific Time for Quora)
            pacific = pytz.timezone('US/Pacific')
            dt_with_tz = pacific.localize(dt)
            
            return dt_with_tz
        except ValueError as e:
            logger.error(f"Error parsing timestamp: {timestamp_str} - {e}")
            return None 