#!/usr/bin/env python3
"""
Quora Answer Processor - Process existing database entries and populate missing fields
"""

import os
import sys
import time
import logging
from datetime import datetime
import pytz
from selenium.webdriver.common.by import By
import html2text
from .database import DatabaseManager
from .chrome_driver_manager import get_chrome_manager

logger = logging.getLogger(__name__)


class QuoraAnswerProcessor:
    """Processes existing answer URLs and populates database with complete answer data"""

    def __init__(self):
        self.chrome_manager = get_chrome_manager()
        self.db_manager = None
        self.processed_count = 0
        self.success_count = 0
        self.total_entries = 0
        self.failed_urls = []
        self.setup_file_logging()

    def setup_file_logging(self):
        """Setup file logging for processed URLs"""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)

        # Create a file handler for processed URLs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.url_log_file = f"logs/processed_urls_{timestamp}.log"

        # Create a separate logger for URL logging
        self.url_logger = logging.getLogger('url_processor')
        self.url_logger.setLevel(logging.INFO)
        # Prevent propagation to root logger (prevents console output)
        self.url_logger.propagate = False

        # Clear any existing handlers to avoid duplicates
        self.url_logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(self.url_log_file)
        file_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.url_logger.addHandler(file_handler)

    def update_progress(self, message, failed=False):
        """Update progress in terminal with single line"""
        if failed:
            # Show failed URLs with newline
            print(f"\n❌ Failed: {message}")
        else:
            # Overwrite the same line for progress
            progress_pct = (self.processed_count / self.total_entries * 100) if self.total_entries > 0 else 0
            status = f"Processing: {self.processed_count}/{self.total_entries} ({progress_pct:.1f}%) | Success: {self.success_count} | Failed: {len(self.failed_urls)}"
            print(f"\r{status}", end="", flush=True)

    def process_existing_entries(self):
        """Process existing database entries and populate missing fields"""
        logger.info("Starting answer processor...")

        # Setup Chrome driver with CDP connection and authentication check
        if not self.chrome_manager.setup_driver():
            logger.error("Failed to setup Chrome driver")
            return False

        if not self.chrome_manager.is_authenticated():
            logger.error("Not authenticated to Quora. Please login in the browser first to authenticate.")
            self.chrome_manager.cleanup()
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
            logger.info(f"Detailed URL logs will be saved to: {self.url_log_file}")
            
            self.processed_count = 0
            self.success_count = 0
            
            for entry in incomplete_entries:
                answered_question_url = entry['answered_question_url']
                entry_id = entry['id']
                
                try:
                    # Log URL to file
                    self.url_logger.info(f"Processing: {answered_question_url}")

                    # Extract data from the answer page
                    answer_data = self.extract_answer_data(answered_question_url)

                    if answer_data:
                        # Double-check critical fields before database update
                        if answer_data.get('question_text') and answer_data.get('answer_content'):
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
                        else:
                            # Critical fields missing - don't update database
                            success = False
                            self.url_logger.error(f"FAILED (Missing critical fields): {answered_question_url}")

                        if success:
                            self.success_count += 1
                            self.url_logger.info("SUCCESS")
                        else:
                            self.failed_urls.append(answered_question_url)
                            self.url_logger.error(f"FAILED (DB Update): {answered_question_url}")
                            self.update_progress(answered_question_url, failed=True)
                    else:
                        self.failed_urls.append(answered_question_url)
                        self.url_logger.error(f"FAILED (Data Extraction): {answered_question_url}")
                        self.update_progress(answered_question_url, failed=True)

                    self.processed_count += 1
                    self.update_progress(answered_question_url)

                    # Add delay between requests to be respectful
                    time.sleep(2)

                except Exception as e:
                    self.failed_urls.append(answered_question_url)
                    self.url_logger.error(f"FAILED (Exception): {answered_question_url} - Error: {e}")
                    self.update_progress(answered_question_url, failed=True)
                    self.processed_count += 1
                    continue
            
            # Final summary
            print()  # New line after progress updates

            # Write summary to log file
            self.url_logger.info("="*80)
            self.url_logger.info(f"PROCESSING SUMMARY")
            self.url_logger.info(f"Total processed: {self.processed_count}")
            self.url_logger.info(f"Successful: {self.success_count}")
            self.url_logger.info(f"Failed: {len(self.failed_urls)}")
            self.url_logger.info("="*80)

            # Terminal summary
            logger.info(f"\nProcessing complete:")
            logger.info(f"  Total processed: {self.processed_count}")
            logger.info(f"  Successful: {self.success_count}")
            logger.info(f"  Failed: {len(self.failed_urls)}")

            if self.failed_urls:
                logger.error(f"\nFailed URLs ({len(self.failed_urls)}):")
                for url in self.failed_urls:
                    logger.error(f"  - {url}")

            logger.info(f"\nDetailed logs saved to: {self.url_log_file}")
            return True
            
        finally:
            if self.db_manager:
                self.db_manager.disconnect()
            self.chrome_manager.cleanup()

    def extract_answer_data(self, answered_question_url: str) -> dict:
        """Extract all required data from an answer page"""
        try:
            # Navigate to the answer page
            self.chrome_manager.get_driver().get(answered_question_url)
            time.sleep(3)  # Wait for page to load
            
            answer_data = {}
            
            # Store the answered question URL
            answer_data['answered_question_url'] = answered_question_url
            
            # Extract question URL
            try:
                question_url_element = self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, "a.puppeteer_test_link:has(.puppeteer_test_question_title)")
                answer_data['question_url'] = question_url_element.get_attribute('href')
            except Exception as e:
                logger.debug(f"Could not extract question URL: {e}")
                answer_data['question_url'] = None
            
            # Extract question text
            try:
                question_text_element = self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, ".puppeteer_test_question_title span")
                answer_data['question_text'] = question_text_element.text.strip()
            except Exception as e:
                logger.debug(f"Could not extract question text: {e}")
                answer_data['question_text'] = None
            
            # Extract answer content and convert to markdown
            # self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, "div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text").get_attribute('innerHTML')
            try:
                answer_content_element = self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, "div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text")
                answer_html = answer_content_element.get_attribute('innerHTML')

                # Configure html2text converter
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0  # Don't wrap lines
                answer_markdown = h.handle(answer_html)
                
                answer_data['answer_content'] = answer_markdown.strip()
            except Exception as e:
                logger.debug(f"Could not extract answer content: {e}")
                answer_data['answer_content'] = None
            
            # Extract revision data from log page
            log_url = f"{answered_question_url}/log"
            try:
                self.chrome_manager.get_driver().get(log_url)
                time.sleep(2)
                
                # Extract revision link
                try:
                    revision_link_element = self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, "a.puppeteer_test_link[href*='/log/revision/']")
                    answer_data['revision_link'] = revision_link_element.get_attribute('href')
                except Exception as e:
                    logger.debug(f"Could not extract revision link: {e}")
                    answer_data['revision_link'] = None
                
                # Extract post timestamp
                try:
                    timestamp_element = self.chrome_manager.get_driver().find_element(By.CSS_SELECTOR, "span.c1h7helg.c8970ew:last-child")
                    timestamp_raw = timestamp_element.text.strip()
                    answer_data['post_timestamp_raw'] = timestamp_raw
                    
                    # Parse timestamp
                    parsed_timestamp = self.parse_quora_timestamp(timestamp_raw)
                    answer_data['post_timestamp_parsed'] = parsed_timestamp
                    
                except Exception as e:
                    logger.debug(f"Could not extract timestamp: {e}")
                    answer_data['post_timestamp_raw'] = None
                    answer_data['post_timestamp_parsed'] = None
                    
            except Exception as e:
                logger.debug(f"Could not access log page {log_url}: {e}")
                answer_data['revision_link'] = None
                answer_data['post_timestamp_raw'] = None
                answer_data['post_timestamp_parsed'] = None

            # Validate critical fields - must have at least question_text and answer_content
            if not answer_data.get('question_text') or not answer_data.get('answer_content'):
                self.url_logger.error(f"Critical fields missing for {answered_question_url} - question_text: {bool(answer_data.get('question_text'))}, answer_content: {bool(answer_data.get('answer_content'))}")
                return None

            return answer_data

        except Exception as e:
            self.url_logger.error(f"Failed to extract data from {answered_question_url}: {e}")
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
        processor.chrome_manager.cleanup() 