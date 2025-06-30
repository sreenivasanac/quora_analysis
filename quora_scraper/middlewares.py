import os
import time
import logging
import platform
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapy.http import HtmlResponse
from scrapy.exceptions import NotConfigured
from webdriver_manager.chrome import ChromeDriverManager
from .common import check_quora_authentication

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware to handle Google OAuth authentication for Quora"""
    
    def __init__(self, email=None):
        self.email = email or os.getenv('GOOGLE_EMAIL', 'sreenivasan.ac92@gmail.com')
        if not self.email:
            raise NotConfigured("GOOGLE_EMAIL environment variable is required")
        
        self.driver = None
        self.authenticated = False
        self.cookies = None
        
        # Disable verbose selenium and urllib3 logging
        logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            email=crawler.settings.get('GOOGLE_EMAIL')
        )
    
    def setup_driver(self):
        """Setup Chrome driver to connect to existing browser or create new one"""
        chrome_options = Options()
        
        # First try to connect to existing Chrome instance
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
                
                # Minimal options for maximum compatibility
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
        """Get Chrome driver service based on platform"""
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
    
    def authenticate_with_google(self):
        # TODO make this more robust, cleaner, and cleanup the code
        """Perform Google OAuth authentication for Quora"""
        if self.authenticated:
            return True
        
        try:
            logger.info("Starting Google OAuth authentication for Quora")
            
            # Check if already logged
            # Navigate to Quora main page to check authentication
            self.driver.get("https://www.quora.com/")
            is_authenticated = check_quora_authentication(self.driver)
            if is_authenticated:
                self.cookies = self.driver.get_cookies()
                self.authenticated = True
                return True
            
            time.sleep(1)  # Brief pause before proceeding to login
            
            # Look for Google login option directly (no need to click Login button first)
            google_login_selectors = [
                ".puppeteer_test_login_button_google",
                "//div[contains(@class, 'puppeteer_test_login_button_google')]",
                "//div[contains(text(), 'Continue with Google')]",
                "//button[contains(text(), 'Continue with Google')]"
            ]
            
            google_clicked = False
            for selector in google_login_selectors:
                try:
                    logger.info(f"Trying Google login selector: {selector}")
                    if selector.startswith("//"):
                        google_login = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        google_login = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    google_login.click()
                    google_clicked = True
                    logger.info(f"Google login clicked using selector: {selector}")
                    time.sleep(2)  # Give more time for redirect
                    break
                except TimeoutException as e:
                    logger.warning(f"Google login selector failed: {selector} - {e}")
                    continue
            
            if not google_clicked:
                logger.error("Google login button not found with any selector")
                logger.info("Current page title: " + self.driver.title)
                logger.info("Current URL: " + self.driver.current_url)
                
                # Maybe we're already logged in but the check failed
                logger.warning("Assuming already logged in and proceeding...")
                self.cookies = self.driver.get_cookies()
                self.authenticated = True
                return True
            
            # Check if we're on Google OAuth page accounts.google.com
            current_url = self.driver.current_url
            if "accounts.google.com" in current_url:
                logger.info("On Google authentication page - looking for account selection...")
                
                # Try to find and click the account that matches our email
                try:
                    # Look for account selection elements with our email
                    account_selectors = [
                        f"[data-identifier='{self.email}']",  # Direct data attribute match
                        f"div[role='link'][data-identifier='{self.email}']",  # More specific role-based selector
                        f"//div[@role='link' and @data-identifier='{self.email}']",  # XPath with role and data-identifier
                        f"[data-email='{self.email}']",       # Alternative data attribute
                        f"//div[contains(text(), '{self.email}')]",  # Text content match
                        f"//div[@data-email='{self.email}']"  # XPath for data-email
                    ]
                    
                    account_clicked = False
                    for selector in account_selectors:
                        try:
                            logger.info(f"Trying account selector: {selector}")
                            if selector.startswith("//"):
                                # XPath selector
                                account_element = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            else:
                                # CSS selector
                                account_element = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            
                            account_element.click()
                            account_clicked = True
                            logger.info(f"Successfully clicked account for {self.email}")
                            time.sleep(2)  # Wait for navigation
                            break
                            
                        except TimeoutException:
                            logger.debug(f"Account selector not found: {selector}")
                            continue
                        except Exception as e:
                            logger.debug(f"Error with selector {selector}: {e}")
                            continue
                    
                    if not account_clicked:
                        logger.warning(f"Could not find account for {self.email} - continuing anyway...")
                    
                except Exception as e:
                    logger.warning(f"Error during account selection: {e}")

            # Wait for authentication to complete (shorter timeout)
            logger.info("Waiting for authentication completion...")
            max_wait_time = 10
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = self.driver.current_url
                
                # Check for successful login indicators
                if "quora.com" in current_url and "login" not in current_url.lower():
                    # Additional check: try to find user-specific elements
                    is_authenticated = check_quora_authentication(self.driver)
                    if is_authenticated:
                        self.cookies = self.driver.get_cookies()
                        self.authenticated = True
                        return True
            
            current_url = self.driver.current_url
            logger.info(f"Current URL: {current_url}")
            
            # Try to proceed anyway - maybe we're logged in
            if "quora.com" in current_url:
                logger.warning("Assuming authentication successful and proceeding...")
                self.cookies = self.driver.get_cookies()
                self.authenticated = True
                return True
            else:
                logger.error("Authentication appears to have failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to authenticate with Google: {e}")
            
            # Try to proceed anyway in case we're already logged in
            try:
                current_url = self.driver.current_url
                if "quora.com" in current_url:
                    logger.warning("Exception occurred but still on Quora - attempting to proceed...")
                    self.cookies = self.driver.get_cookies()
                    self.authenticated = True
                    return True
            except:
                pass
                
            return False
    
    def process_request(self, request, spider):
        """Process request with authentication if needed"""
        # # Check if this is a Selenium-only request (no HTTP needed)
        # if request.meta.get('use_selenium', False):
        #     logger.info("Skipping HTTP request - using Selenium directly")
        #     # Return a fake response since we'll handle everything in Selenium
        #     return HtmlResponse(
        #         url=request.url,
        #         body=b'<html><body>Selenium will handle this</body></html>',
        #         encoding='utf-8'
        #     )
        
        # For regular HTTP requests, ensure authentication
        if not self.authenticated:
            if not self.driver:
                self.setup_driver()
            
            if not self.authenticate_with_google():
                logger.error("Authentication failed, cannot proceed")
                return None
        
        # Add cookies to request
        if self.cookies:
            cookie_dict = {cookie['name']: cookie['value'] for cookie in self.cookies}
            request.cookies.update(cookie_dict)
        
        return None
    
    def spider_closed(self, spider):
        """Clean up when spider closes"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed") 