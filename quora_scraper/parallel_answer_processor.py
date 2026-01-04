#!/usr/bin/env python3
"""
Parallel Quora Answer Processor - Process answers in parallel using multiple Chrome instances
"""

import os
import sys
import time
import logging
import multiprocessing as mp
from multiprocessing import Pool, Manager, Queue
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pytz
from selenium.webdriver.common.by import By
import html2text
import requests

from .database_sqlite import DatabaseManager
from .chrome_driver_manager import ChromeDriverManager
from .common import check_quora_authentication

# Configure main logger only
logger = logging.getLogger(__name__)


class ParallelChromeManager(ChromeDriverManager):
    """Chrome manager for parallel processing with specific port"""

    def __init__(self, debug_port: int = 9223):
        super().__init__()
        self.debug_port = debug_port
        self.driver = None
        self.authenticated = False

    def connect_to_existing_chrome(self):
        """Override to use specific debug port"""
        cdp_url = f'http://localhost:{self.debug_port}'

        try:
            logger.info(f'Worker connecting to Chrome on port {self.debug_port}...')

            # Check if Chrome is running on this port
            response = requests.get(f'{cdp_url}/json', timeout=2)
            if response.status_code == 200:
                tabs_info = response.json()
                logger.info(f"Worker found Chrome with {len(tabs_info)} tabs on port {self.debug_port}")

                # Connect to Chrome via debuggerAddress
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service

                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')

                service = self.get_chrome_service()

                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                # Apply stealth mode
                self.apply_stealth_mode()

                # Check authentication
                current_url = self.driver.current_url
                logger.info(f"Worker connected to Chrome on port {self.debug_port}")

                return True
            else:
                return False

        except Exception as e:
            logger.debug(f"Could not connect to Chrome on port {self.debug_port}: {e}")
            return False

    def start_chrome_with_debugging(self):
        """Start Chrome with specific debug port"""
        try:
            import platform
            import subprocess

            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'

            if is_mac_arm:
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            else:
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                if not os.path.exists(chrome_path):
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

            # Start Chrome with specific port
            chrome_cmd = [
                chrome_path,
                f'--remote-debugging-port={self.debug_port}',
                f'--user-data-dir=/tmp/chrome_debug_profile_{self.debug_port}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--new-window'
            ]

            logger.info(f"Starting Chrome on port {self.debug_port}...")
            subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for Chrome to start
            time.sleep(3)

            # Verify Chrome started
            response = requests.get(f'http://localhost:{self.debug_port}/json', timeout=5)
            if response.status_code == 200:
                logger.info(f"Chrome started successfully on port {self.debug_port}")
                return True
            else:
                raise Exception(f"Chrome started but debugging not accessible on port {self.debug_port}")

        except Exception as e:
            logger.error(f"Failed to start Chrome on port {self.debug_port}: {e}")
            return False


def setup_worker_logging(worker_id: int, log_dir: str = "logs"):
    """Setup file-only logging for a worker"""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/worker_{worker_id}_{timestamp}.log"

    # Create a dedicated logger for this worker
    worker_logger = logging.getLogger(f'worker_{worker_id}')
    worker_logger.setLevel(logging.INFO)
    worker_logger.propagate = False  # Don't propagate to root logger

    # Clear any existing handlers
    worker_logger.handlers.clear()

    # Create file handler only (no console output)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    worker_logger.addHandler(file_handler)

    return worker_logger, log_file


def worker_process_answers(args: Tuple[int, List[Dict], int, Queue, Queue, str]):
    """
    Worker function to process a chunk of answers

    Args:
        args: Tuple of (worker_id, url_chunks, debug_port, progress_queue, failed_queue, log_dir)
    """
    worker_id, url_chunk, debug_port, progress_queue, failed_queue, log_dir = args

    # Setup file-only logging for this worker
    worker_logger, log_file = setup_worker_logging(worker_id, log_dir)
    worker_logger.info(f"Worker {worker_id} started with {len(url_chunk)} URLs on port {debug_port}")
    worker_logger.info(f"Log file: {log_file}")

    # Create Chrome manager for this worker
    chrome_manager = ParallelChromeManager(debug_port=debug_port)

    # Setup Chrome driver
    if not chrome_manager.setup_driver():
        worker_logger.error(f"Worker {worker_id}: Failed to setup Chrome driver on port {debug_port}")
        return

    # Check authentication
    if not chrome_manager.is_authenticated():
        worker_logger.error(f"Worker {worker_id}: Not authenticated to Quora")
        chrome_manager.cleanup()
        return

    # Create database connection for this worker
    db_manager = DatabaseManager()
    db_manager.connect()

    # Process URLs
    processed_count = 0
    success_count = 0

    try:
        for entry in url_chunk:
            answered_question_url = entry['answered_question_url']
            entry_id = entry['id']

            try:
                # Extract data from the answer page
                answer_data = extract_answer_data_worker(chrome_manager, answered_question_url, worker_logger)

                if answer_data:
                    # Check critical fields
                    if answer_data.get('question_text') and answer_data.get('answer_content'):
                        # Update database
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
                            worker_logger.info(f"SUCCESS: {answered_question_url}")
                        else:
                            failed_queue.put(answered_question_url)
                            worker_logger.error(f"FAILED (DB Update): {answered_question_url}")
                    else:
                        failed_queue.put(answered_question_url)
                        worker_logger.error(f"FAILED (Missing fields): {answered_question_url}")
                else:
                    failed_queue.put(answered_question_url)
                    worker_logger.error(f"FAILED (Extraction): {answered_question_url}")

                processed_count += 1

                # Send progress update
                progress_queue.put({
                    'worker_id': worker_id,
                    'processed': processed_count,
                    'success': success_count,
                    'total': len(url_chunk)
                })

                # Respectful delay
                time.sleep(0.5)  # Shorter delay since we have multiple workers

            except Exception as e:
                # Check for session errors and attempt recovery
                if "invalid session id" in str(e).lower():
                    worker_logger.error(f"Chrome session died. Attempting to reconnect...")
                    # Try to reconnect
                    chrome_manager.cleanup()
                    if chrome_manager.setup_driver():
                        worker_logger.info(f"Successfully reconnected Chrome")
                        # Retry the current URL
                        continue
                    else:
                        worker_logger.error(f"Failed to reconnect Chrome. Worker shutting down.")
                        break
                else:
                    worker_logger.error(f"Error processing {answered_question_url}: {e}")

                failed_queue.put(answered_question_url)
                processed_count += 1
                continue

    finally:
        # Cleanup
        db_manager.disconnect()
        chrome_manager.cleanup()
        worker_logger.info(f"Worker completed: {success_count}/{processed_count} successful")
        worker_logger.info(f"Worker {worker_id} shutting down")


def extract_answer_data_worker(chrome_manager: ParallelChromeManager, answered_question_url: str, logger) -> Optional[Dict]:
    """Extract answer data for a worker"""
    try:
        # Clean the URL by removing ?no_redirect=1 if present
        cleaned_url = answered_question_url.split('?no_redirect=1')[0]

        # Navigate to the answer page
        chrome_manager.get_driver().get(answered_question_url)
        time.sleep(3)  # Wait for page to load

        answer_data = {}
        answer_data['answered_question_url'] = cleaned_url
        answered_question_url = cleaned_url

        # Extract question URL
        try:
            question_url_element = chrome_manager.get_driver().find_element(
                By.CSS_SELECTOR, "a.puppeteer_test_link:has(.puppeteer_test_question_title)"
            )
            answer_data['question_url'] = question_url_element.get_attribute('href')
        except Exception:
            answer_data['question_url'] = None

        # Extract question text
        try:
            question_text_element = chrome_manager.get_driver().find_element(
                By.CSS_SELECTOR, ".puppeteer_test_question_title span"
            )
            answer_data['question_text'] = question_text_element.text.strip()
        except Exception:
            answer_data['question_text'] = None

        # Extract answer content
        try:
            answer_content_element = chrome_manager.get_driver().find_element(
                By.CSS_SELECTOR, "div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text"
            )
            answer_html = answer_content_element.get_attribute('innerHTML')

            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0
            answer_markdown = h.handle(answer_html)

            answer_data['answer_content'] = answer_markdown.strip()
        except Exception:
            answer_data['answer_content'] = None

        # Extract revision data from log page
        log_url = f"{answered_question_url}/log"
        try:
            chrome_manager.get_driver().get(log_url)
            time.sleep(2)

            # Extract revision link
            try:
                revision_link_element = chrome_manager.get_driver().find_element(
                    By.CSS_SELECTOR, "a.puppeteer_test_link[href*='/log/revision/']"
                )
                answer_data['revision_link'] = revision_link_element.get_attribute('href')
            except Exception:
                answer_data['revision_link'] = None

            # Extract timestamp
            try:
                timestamp_element = chrome_manager.get_driver().find_element(
                    By.CSS_SELECTOR, "span.c1h7helg.c8970ew:last-child"
                )
                timestamp_raw = timestamp_element.text.strip()
                answer_data['post_timestamp_raw'] = timestamp_raw

                # Parse timestamp
                parsed_timestamp = parse_quora_timestamp(timestamp_raw)
                answer_data['post_timestamp_parsed'] = parsed_timestamp

            except Exception:
                answer_data['post_timestamp_raw'] = None
                answer_data['post_timestamp_parsed'] = None

        except Exception:
            answer_data['revision_link'] = None
            answer_data['post_timestamp_raw'] = None
            answer_data['post_timestamp_parsed'] = None

        # Validate critical fields
        if not answer_data.get('question_text') or not answer_data.get('answer_content'):
            return None

        return answer_data

    except Exception as e:
        logger.error(f"Failed to extract data from {answered_question_url}: {e}")
        return None


def parse_quora_timestamp(timestamp_str: str):
    """Parse Quora timestamp string"""
    if not timestamp_str:
        return None

    try:
        dt = datetime.strptime(timestamp_str, "%B %d, %Y at %I:%M:%S %p")
        ist = pytz.timezone('Asia/Kolkata')
        dt_with_tz = ist.localize(dt)
        return dt_with_tz
    except ValueError:
        return None


class ParallelAnswerProcessor:
    """Main class for parallel answer processing"""

    def __init__(self, num_workers: int = 3):
        self.num_workers = min(num_workers, 5)  # Max 5 workers
        self.base_debug_port = 9223
        self.failed_urls = []
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for parallel processing coordinator"""
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = f"logs/parallel_{timestamp}"
        os.makedirs(self.log_dir, exist_ok=True)

        # Main coordinator log file
        self.log_file = f"{self.log_dir}/coordinator.log"

        # Setup main logger for coordinator only
        self.coordinator_logger = logging.getLogger('coordinator')
        self.coordinator_logger.setLevel(logging.INFO)
        self.coordinator_logger.propagate = False

        # Clear existing handlers
        self.coordinator_logger.handlers.clear()

        # File handler only for coordinator
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.coordinator_logger.addHandler(file_handler)

    def ensure_chrome_instances(self):
        """Ensure Chrome instances are running on required ports"""
        ports_needed = []

        for i in range(self.num_workers):
            port = self.base_debug_port + i
            try:
                # Check if Chrome is already running on this port
                response = requests.get(f'http://localhost:{port}/json', timeout=1)
                if response.status_code == 200:
                    self.coordinator_logger.info(f"Chrome already running on port {port}")
                else:
                    ports_needed.append(port)
            except:
                ports_needed.append(port)

        # Start Chrome instances for missing ports
        for port in ports_needed:
            self.coordinator_logger.info(f"Starting Chrome on port {port}...")
            chrome_manager = ParallelChromeManager(debug_port=port)
            if chrome_manager.start_chrome_with_debugging():
                self.coordinator_logger.info(f"Successfully started Chrome on port {port}")
            else:
                self.coordinator_logger.error(f"Failed to start Chrome on port {port}")

        # Give Chrome instances time to fully start
        if ports_needed:
            time.sleep(5)
        else:
            self.coordinator_logger.info("All required Chrome instances are already running")

    def divide_work(self, entries: List[Dict]) -> List[List[Dict]]:
        """Divide entries into chunks for workers"""
        chunk_size = len(entries) // self.num_workers
        remainder = len(entries) % self.num_workers

        chunks = []
        start = 0

        for i in range(self.num_workers):
            # Add 1 to chunk size for first 'remainder' workers to handle the remainder
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end = start + current_chunk_size

            if current_chunk_size > 0:
                chunks.append(entries[start:end])

            start = end

        return chunks

    def process_entries_parallel(self):
        """Main method to process entries in parallel"""
        print(f"\n{'='*70}")
        print(f"Starting Parallel Processing with {self.num_workers} workers")
        print(f"{'='*70}")
        self.coordinator_logger.info(f"Starting parallel processing with {self.num_workers} workers")

        # Ensure Chrome instances are running
        self.ensure_chrome_instances()

        # Get incomplete entries from database
        db_manager = DatabaseManager()
        db_manager.connect()

        try:
            incomplete_entries = db_manager.get_incomplete_entries()
            total_entries = len(incomplete_entries)

            if total_entries == 0:
                print("No incomplete entries found in database")
                self.coordinator_logger.info("No incomplete entries found")
                return True

            print(f"Found {total_entries} entries to process")
            print(f"Workers: {self.num_workers}")
            print(f"Entries per worker: ~{total_entries // self.num_workers}")
            print(f"Log directory: {self.log_dir}")
            print(f"{'='*70}\n")

            self.coordinator_logger.info(f"Found {total_entries} incomplete entries")
            self.coordinator_logger.info(f"Using {self.num_workers} workers")

            # Divide work among workers
            chunks = self.divide_work(incomplete_entries)

            # Create manager for shared data
            manager = Manager()
            progress_queue = manager.Queue()
            failed_queue = manager.Queue()

            # Prepare worker arguments
            worker_args = []
            for i, chunk in enumerate(chunks):
                if chunk:  # Only add workers with actual work
                    port = self.base_debug_port + i
                    worker_args.append((i, chunk, port, progress_queue, failed_queue, self.log_dir))

            # Start worker pool
            with Pool(processes=len(worker_args)) as pool:
                # Start workers
                results = pool.map_async(worker_process_answers, worker_args)

                # Monitor progress
                self.monitor_progress(progress_queue, failed_queue, total_entries, len(worker_args))

                # Wait for completion
                results.wait()

            # Collect failed URLs
            while not failed_queue.empty():
                self.failed_urls.append(failed_queue.get())

            # Final summary
            print(f"\n{'='*70}")
            print("PARALLEL PROCESSING COMPLETE")
            print(f"{'='*70}")
            print(f"Total entries processed: {total_entries}")
            print(f"Failed: {len(self.failed_urls)}")
            print(f"\nLogs saved to: {self.log_dir}/")
            print(f"  Coordinator log: coordinator.log")
            for i in range(len(worker_args)):
                print(f"  Worker {i} log: worker_{i}_*.log")

            self.coordinator_logger.info("="*80)
            self.coordinator_logger.info("PROCESSING COMPLETE")
            self.coordinator_logger.info(f"Total: {total_entries}, Failed: {len(self.failed_urls)}")

            if self.failed_urls:
                print(f"\n❌ Failed URLs ({len(self.failed_urls)}):")
                self.coordinator_logger.error(f"Failed URLs ({len(self.failed_urls)}):")
                for url in self.failed_urls[:5]:  # Show first 5 in terminal
                    print(f"  - {url}")
                if len(self.failed_urls) > 5:
                    print(f"  ... and {len(self.failed_urls) - 5} more (see log file)")

                # Write all to log
                for url in self.failed_urls:
                    self.coordinator_logger.error(f"  - {url}")

            return True

        finally:
            db_manager.disconnect()

    def monitor_progress(self, progress_queue: Queue, failed_queue: Queue, total: int, num_workers: int):
        """Monitor and display progress from all workers"""
        worker_progress = {i: {'processed': 0, 'success': 0} for i in range(num_workers)}

        start_time = time.time()
        last_update = 0

        while True:
            # Check for progress updates
            while not progress_queue.empty():
                try:
                    update = progress_queue.get_nowait()
                    worker_id = update['worker_id']
                    worker_progress[worker_id] = {
                        'processed': update['processed'],
                        'success': update['success']
                    }
                except:
                    break

            # Calculate totals
            total_processed = sum(w['processed'] for w in worker_progress.values())
            total_success = sum(w['success'] for w in worker_progress.values())

            # Update display every second
            current_time = time.time()
            if current_time - last_update >= 1:
                elapsed = int(current_time - start_time)
                progress_pct = (total_processed / total * 100) if total > 0 else 0

                # Calculate rate
                rate = total_processed / elapsed if elapsed > 0 else 0
                eta = int((total - total_processed) / rate) if rate > 0 else 0

                # Format time remaining
                eta_min = eta // 60
                eta_sec = eta % 60
                eta_str = f"{eta_min}m {eta_sec}s" if eta_min > 0 else f"{eta_sec}s"

                status = (f"\r⚡ Progress: {total_processed}/{total} ({progress_pct:.1f}%) | "
                         f"✓ Success: {total_success} | "
                         f"⚡ Rate: {rate:.1f}/s | "
                         f"⏱ ETA: {eta_str} | "
                         f"👥 Workers: {num_workers}")

                print(status, end="", flush=True)
                last_update = current_time

            # Check if all done
            if total_processed >= total:
                print()  # New line after progress
                self.coordinator_logger.info(f"All {total} entries processed")
                break

            time.sleep(0.1)  # Small delay to prevent CPU spinning


def run_parallel_processor(num_workers: int = 3):
    """Main entry point for parallel processing"""
    processor = ParallelAnswerProcessor(num_workers=num_workers)

    try:
        success = processor.process_entries_parallel()
        return success
    except KeyboardInterrupt:
        logger.info("Parallel processing interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error during parallel processing: {e}")
        return False