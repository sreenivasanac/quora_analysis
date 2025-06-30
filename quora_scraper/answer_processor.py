#!/usr/bin/env python3
"""
Quora Answer Processor - Process existing database entries and populate missing fields
"""

import os
import time
import logging
import platform
import subprocess
import requests
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
import html2text
from webdriver_manager.chrome import ChromeDriverManager
from .database import DatabaseManager
from .common import check_quora_authentication

logger = logging.getLogger(__name__)


class QuoraAnswerProcessor:
    """Processes existing answer URLs and populates database with complete answer data"""
    
    def __init__(self):
        self.driver = None
        self.db_manager = None
        self.processed_count = 0
        self.success_count = 0
        self.total_entries = 0
        self.authenticated = False
        
        # Disable verbose selenium and urllib3 logging
        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    
    def setup_selenium_driver(self):
        """Setup Selenium driver using CDP connection (same as middleware)"""
        if self.driver is None:
            # First try to connect to existing Chrome instance (same as middleware)
            if self.connect_to_existing_chrome():
                return
            
            # If no existing instance, start Chrome with remote debugging
            logger.info("No existing Chrome instance found, starting Chrome with remote debugging")
            self.start_chrome_with_debugging()
            
            # Now connect to the Chrome instance we just started
            if not self.connect_to_existing_chrome():
                raise Exception("Failed to connect to Chrome instance")
    
    def connect_to_existing_chrome(self):
        """Try to connect to existing Chrome instance with remote debugging enabled (CDP)"""
        debug_port = 9222
        cdp_url = f'http://localhost:{debug_port}'
        
        try:
            logger.info(f'Attempting to connect to Chrome via CDP at {cdp_url}...')
            
            # Check if Chrome is running with remote debugging (similar to Playwright's connectOverCDP)
            response = requests.get(f'{cdp_url}/json', timeout=5)
            if response.status_code == 200:
                tabs_info = response.json()
                logger.info(f"Found existing Chrome instance with {len(tabs_info)} tabs on port {debug_port}")
                
                # Log some tab information for debugging (similar to Playwright's approach)
                for i, tab in enumerate(tabs_info[:3]):  # Show first 3 tabs
                    logger.info(f"  Tab {i+1}: {tab.get('title', 'Unknown')} - {tab.get('url', 'Unknown URL')}")
                
                # Connect to Chrome via debuggerAddress (Selenium's equivalent of connectOverCDP)
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
                
                # Minimal options for maximum compatibility (same as middleware)
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                # Setup Chrome driver service
                service = self.get_chrome_service()
                
                logger.info("Establishing CDP connection to existing Chrome session...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Execute script to remove webdriver property (stealth mode)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Verify connection by getting current page info
                current_url = self.driver.current_url
                current_title = self.driver.title
                logger.info(f"Successfully connected to Chrome session!")
                logger.info(f"Current page: {current_title} ({current_url})")
                
                # Check if already authenticated to Quora
                is_authenticated = check_quora_authentication(self.driver)
                logger.info(f"Quora authentication status: {is_authenticated}")
                
                return True
            else:
                logger.info(f"Chrome debugging endpoint returned status {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.info(f"Could not reach Chrome debugging endpoint: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to existing Chrome instance: {e}")
            return False
    
    def start_chrome_with_debugging(self):
        """Start Chrome with remote debugging enabled (same as middleware)"""
        debug_port = 9222
        
        try:
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
            
            if is_mac_arm:
                logger.info("Detected Mac ARM architecture")
                # Ensure Chrome is installed via Homebrew
                subprocess.run(['brew', 'install', '--cask', 'google-chrome'], 
                             capture_output=True, check=False)
                
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            else:
                # For Intel Macs and other systems
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                if not os.path.exists(chrome_path):
                    # Try common Chrome paths
                    possible_paths = [
                        '/usr/bin/google-chrome',
                        '/usr/bin/chromium-browser',
                        'google-chrome'
                    ]
                    for path in possible_paths:
                        if os.path.exists(path) or subprocess.run(['which', path], 
                                                                capture_output=True).returncode == 0:
                            chrome_path = path
                            break
            
            # Start Chrome with remote debugging
            chrome_cmd = [
                chrome_path,
                f'--remote-debugging-port={debug_port}',
                '--user-data-dir=/tmp/chrome_debug_profile',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps'
            ]
            
            logger.info(f"Starting Chrome with command: {' '.join(chrome_cmd)}")
            subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for Chrome to start
            time.sleep(3)
            
            # Verify Chrome started with debugging
            response = requests.get(f'http://localhost:{debug_port}/json', timeout=5)
            if response.status_code == 200:
                logger.info("Chrome started successfully with remote debugging")
            else:
                raise Exception("Chrome started but remote debugging not accessible")
                
        except Exception as e:
            logger.error(f"Failed to start Chrome with debugging: {e}")
            raise
    
    def get_chrome_service(self):
        """Get Chrome driver service based on platform (same as middleware)"""
        try:
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
            
            if is_mac_arm:
                logger.info("Setting up ChromeDriver for Mac ARM")
                # Ensure ChromeDriver is installed via Homebrew
                subprocess.run(['brew', 'install', 'chromedriver'], capture_output=True, check=False)
                # Remove quarantine attribute
                subprocess.run(['xattr', '-d', 'com.apple.quarantine', '/opt/homebrew/bin/chromedriver'], 
                             capture_output=True, check=False)
                
                chromedriver_path = '/opt/homebrew/bin/chromedriver'
                if os.path.exists(chromedriver_path):
                    return Service(executable_path=chromedriver_path)
            
            # For other systems or if homebrew path doesn't exist, use webdriver-manager
            logger.info("Using webdriver-manager to get ChromeDriver")
            return Service(ChromeDriverManager().install())
            
        except Exception as e:
            logger.error(f"Error setting up Chrome service: {e}")
            # Fallback to system chromedriver
            return Service()

    def cleanup_driver(self):
        """Clean up Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Selenium driver cleaned up")

    def process_existing_entries(self):
        """Process existing database entries and populate missing fields"""
        logger.info("Starting to process existing database entries")
        
        # Setup Selenium driver with CDP connection and authentication check
        self.setup_selenium_driver()
        
        if not self.authenticated:
            logger.error("Not authenticated to Quora. Please login in the browser first to authenticate.")
            self.cleanup_driver()
            return False
        
        # Connect to database and get incomplete entries
        self.db_manager = DatabaseManager()
        self.db_manager.connect()
        
        try:
            incomplete_entries = self.db_manager.get_incomplete_entries()
            self.total_entries = len(incomplete_entries)
            
            if self.total_entries == 0:
                logger.info("No incomplete entries found in database")
                return True
            
            logger.info(f"Found {self.total_entries} incomplete entries to process")
            
            self.processed_count = 0
            self.success_count = 0
            
            for entry in incomplete_entries:
                answered_question_url = entry['answered_question_url']
                entry_id = entry['id']
                
                try:
                    logger.info(f"Processing entry {self.processed_count + 1}/{self.total_entries}: {answered_question_url}")
                    
                    # Extract data from the answer page
                    answer_data = self.extract_answer_data(answered_question_url)
                    
                    if answer_data:
                        # Update database with extracted data
                        success = self.db_manager.update_answer_data(
                            answered_question_url=answered_question_url,
                            question_url=answer_data.get('question_url'),
                            question_text=answer_data.get('question_text'),
                            answer_content=answer_data.get('answer_content'),
                            revision_link=answer_data.get('revision_link'),
                            post_timestamp_raw=answer_data.get('post_timestamp_raw'),
                            post_timestamp_parsed=answer_data.get('post_timestamp_parsed')
                        )
                        
                        if success:
                            self.success_count += 1
                            logger.info(f"Successfully updated entry {entry_id}")
                        else:
                            logger.error(f"Failed to update database for entry {entry_id}")
                    else:
                        logger.error(f"Failed to extract data for entry {entry_id}")
                    
                    self.processed_count += 1
                    
                    # Log progress every 50 entries
                    if self.processed_count % 50 == 0:
                        logger.info(f"Progress: {self.processed_count}/{self.total_entries} processed, {self.success_count} successful")
                    
                    # Add delay between requests to be respectful
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing entry {entry_id}: {e}")
                    self.processed_count += 1
                    continue
            
            logger.info(f"Processing complete: {self.processed_count} entries processed, {self.success_count} successful")
            return True
            
        finally:
            if self.db_manager:
                self.db_manager.disconnect()
            self.cleanup_driver()

    def extract_answer_data(self, answered_question_url: str) -> dict:
        """Extract all required data from an answer page"""
        try:
            # Navigate to the answer page
            self.driver.get(answered_question_url)
            time.sleep(3)  # Wait for page to load
            
            answer_data = {}
            
            # Store the answered question URL
            answer_data['answered_question_url'] = answered_question_url
            
            # Extract question URL
            try:
                question_url_element = self.driver.find_element(By.CSS_SELECTOR, "a.puppeteer_test_link:has(.puppeteer_test_question_title)")
                answer_data['question_url'] = question_url_element.get_attribute('href')
            except Exception as e:
                logger.warning(f"Could not extract question URL: {e}")
                answer_data['question_url'] = None
            
            # Extract question text
            try:
                question_text_element = self.driver.find_element(By.CSS_SELECTOR, ".puppeteer_test_question_title span")
                answer_data['question_text'] = question_text_element.text.strip()
            except Exception as e:
                logger.warning(f"Could not extract question text with either selector: {e}")
                answer_data['question_text'] = None
            
            # Extract answer content and convert to markdown
            # self.driver.find_element(By.CSS_SELECTOR, "div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text").get_attribute('innerHTML')
            try:
                answer_content_element = self.driver.find_element(By.CSS_SELECTOR, "div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text")
                answer_html = answer_content_element.get_attribute('innerHTML')

                # Configure html2text converter
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0  # Don't wrap lines
                answer_markdown = h.handle(answer_html)
                
                answer_data['answer_content'] = answer_markdown.strip()
            except Exception as e:
                logger.warning(f"Could not extract answer content: {e}")
                answer_data['answer_content'] = None
            
            # Extract revision data from log page
            log_url = f"{answered_question_url}/log"
            try:
                self.driver.get(log_url)
                time.sleep(2)
                
                # Extract revision link
                try:
                    revision_link_element = self.driver.find_element(By.CSS_SELECTOR, "a.puppeteer_test_link[href*='/log/revision/']")
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
        """Convert Quora timestamp string to datetime object timezone"""
        if not timestamp_str:
            return None
            
        try:
            # Parse the timestamp string (e.g., "June 27, 2025 at 10:26:56 PM")
            dt = datetime.strptime(timestamp_str, "%B %d, %Y at %I:%M:%S %p")
            
            # Set timezone to Indian Standard Time (IST)
            ist = pytz.timezone('Asia/Kolkata')
            dt_with_tz = ist.localize(dt)
            
            return dt_with_tz
        except ValueError as e:
            logger.error(f"Error parsing timestamp: {timestamp_str} - {e}")
            return None


def run_answer_processor():
    """Main function to run the answer processor"""
    processor = QuoraAnswerProcessor()
    
    try:
        success = processor.process_existing_entries()
        return success
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return False
    finally:
        processor.cleanup_driver() 