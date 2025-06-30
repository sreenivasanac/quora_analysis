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
        
        # Disable verbose selenium and urllib3 logging
        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        
        # Load existing URLs from database at startup
        self.load_existing_urls_from_database()
        
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
            # Remove problematic options that aren't compatible with ChromeDriver 138
            # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # chrome_options.add_experimental_option('useAutomationExtension', False)
            # Comment out headless for debugging
            # chrome_options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Selenium driver initialized for scrolling")

    def parse_with_selenium(self, response):
        """Parse answers page with 300-second scrolling to load all content"""

        if not check_quora_authentication(self.driver):
            logger.error("Not authenticated to Quora. Please login in the browser first to authenticate.")
            import pdb; pdb.set_trace()
            return

        logger.info(f"Starting to process {response.url}")
        logger.info(f"Database contains {len(self.database_saved_urls)} existing URLs to skip")
        
        # Setup Selenium driver if not already done
        self.setup_selenium_driver()
        
        # Load the page in Selenium
        self.driver.get(response.url)
        time.sleep(5)  # Wait for initial page load
        
        # Scroll for 300 seconds and collect all answer links
        number_of_seconds_to_scroll = len(self.database_saved_urls)
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

 