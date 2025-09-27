#!/usr/bin/env python3
"""
Chrome Driver Manager - Centralized Chrome driver operations for Quora scraper
Eliminates code duplication across middleware, answer_processor, and spider
"""

import os
import time
import logging
import platform
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from .common import check_quora_authentication

logger = logging.getLogger(__name__)


class ChromeDriverManager:
    """Centralized Chrome driver management for Quora scraper"""

    def __init__(self):
        self.driver = None
        self.authenticated = False
        self.debug_port = 9222

        # Disable verbose selenium and urllib3 logging
        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

    def setup_driver(self):
        """Setup Chrome driver - try CDP connection first, then fallback to new instance"""
        if self.driver is not None:
            logger.info("Chrome driver already initialized")
            return True

        logger.info("Setting up Chrome driver...")

        # First try to connect to existing Chrome instance
        if self.connect_to_existing_chrome():
            logger.info("Successfully connected to existing Chrome instance")
            self.check_authentication()
            return True

        # If no existing instance, start Chrome with debugging
        logger.info("No existing Chrome instance found, starting Chrome with remote debugging")
        if self.start_chrome_with_debugging():
            # Now connect to the Chrome instance we just started
            if self.connect_to_existing_chrome():
                logger.info("Successfully connected to newly started Chrome instance")
                self.check_authentication()
                return True

        logger.error("Failed to setup Chrome driver")
        return False

    def connect_to_existing_chrome(self):
        """Try to connect to existing Chrome instance with remote debugging enabled"""
        cdp_url = f'http://localhost:{self.debug_port}'

        try:
            logger.info(f'Attempting to connect to Chrome via CDP at {cdp_url}...')

            # Check if Chrome is running with remote debugging
            response = requests.get(f'{cdp_url}/json', timeout=5)
            if response.status_code == 200:
                tabs_info = response.json()
                logger.debug(f"Found existing Chrome instance with {len(tabs_info)} tabs on port {self.debug_port}")

                # Connect to Chrome via debuggerAddress
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")

                # Minimal options for maximum compatibility
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')

                # Setup Chrome driver service
                service = self.get_chrome_service()

                logger.debug("Establishing CDP connection to existing Chrome session...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                # Apply stealth mode
                self.apply_stealth_mode()

                # Verify connection by getting current page info
                current_url = self.driver.current_url
                current_title = self.driver.title
                logger.info(f"Successfully connected to Chrome session!")
                logger.debug(f"Current page: {current_title} ({current_url})")

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
        """Start Chrome with remote debugging enabled"""
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
                f'--remote-debugging-port={self.debug_port}',
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
            response = requests.get(f'http://localhost:{self.debug_port}/json', timeout=5)
            if response.status_code == 200:
                logger.info("Chrome started successfully with remote debugging")
                return True
            else:
                raise Exception("Chrome started but remote debugging not accessible")

        except Exception as e:
            logger.error(f"Failed to start Chrome with debugging: {e}")
            return False

    def get_chrome_service(self):
        """Get Chrome driver service based on platform"""
        try:
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'

            if is_mac_arm:
                logger.debug("Setting up ChromeDriver for Mac ARM")
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

    def apply_stealth_mode(self):
        """Apply stealth mode script to hide webdriver property"""
        if not self.driver:
            return

        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.debug("Successfully applied stealth mode")
        except Exception as e:
            logger.debug(f"Stealth mode script failed (may already be applied): {e}")

    def check_authentication(self):
        """Check if authenticated to Quora and update status"""
        if not self.driver:
            self.authenticated = False
            return False

        # Navigate to Quora if not already there
        current_url = self.driver.current_url
        if 'quora.com' not in current_url:
            self.driver.get("https://www.quora.com/")
            time.sleep(2)

        self.authenticated = check_quora_authentication(self.driver)

        if self.authenticated:
            logger.info("Chrome driver is authenticated to Quora")
        else:
            logger.warning("Chrome driver is not authenticated to Quora")

        return self.authenticated

    def get_driver(self):
        """Get the Chrome driver instance, setting it up if necessary"""
        if self.driver is None:
            self.setup_driver()
        return self.driver

    def is_authenticated(self):
        """Check if driver is authenticated to Quora"""
        return self.authenticated

    def cleanup(self):
        """Clean up Chrome driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver cleaned up successfully")
            except Exception as e:
                logger.warning(f"Error during Chrome driver cleanup: {e}")
            finally:
                self.driver = None
                self.authenticated = False


# Global instance for sharing across components
_chrome_manager = None

def get_chrome_manager():
    """Get the global Chrome driver manager instance"""
    global _chrome_manager
    if _chrome_manager is None:
        _chrome_manager = ChromeDriverManager()
    return _chrome_manager

def cleanup_chrome_manager():
    """Cleanup the global Chrome driver manager"""
    global _chrome_manager
    if _chrome_manager:
        _chrome_manager.cleanup()
        _chrome_manager = None