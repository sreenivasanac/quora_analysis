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
        """Perform Google OAuth authentication for Quora"""
        if self.authenticated:
            return True
        
        try:
            logger.info("Starting Google OAuth authentication for Quora")
            
            # Navigate to Quora login page
            self.driver.get("https://www.quora.com/")
            time.sleep(3)
            
            # Check if already logged in by looking for user-specific elements
            try:
                # Look for elements that indicate we're already logged in
                logged_in_indicators = [
                    ".header_login_text_name",  # User name in header
                    ".header_user_menu",        # User menu dropdown
                    "[data-testid='user-menu']", # User menu button
                    ".user_menu_button"         # Alternative user menu
                ]
                
                for indicator in logged_in_indicators:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                        if element and element.is_displayed():
                            logger.info(f"Already logged in to Quora (found: {indicator})")
                            self.cookies = self.driver.get_cookies()
                            self.authenticated = True
                            return True
                    except:
                        continue
                        
                # Also check the URL - if we're not on login page, might be logged in
                current_url = self.driver.current_url
                if "login" not in current_url.lower() and "quora.com" in current_url:
                    # Try to navigate to a protected page to test authentication
                    test_url = "https://www.quora.com/profile/Kanthaswamy-Balasubramaniam/answers"
                    self.driver.get(test_url)
                    time.sleep(3)
                    
                    # If we can access the profile page, we're logged in
                    if "profile" in self.driver.current_url:
                        logger.info("Already logged in to Quora (can access profile pages)")
                        self.cookies = self.driver.get_cookies()
                        self.authenticated = True
                        return True
                    else:
                        # Go back to main page for login
                        self.driver.get("https://www.quora.com/")
                        time.sleep(2)
                        
            except Exception as e:
                logger.debug(f"Error checking login status: {e}")
            
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
                    time.sleep(3)  # Give more time for redirect
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
            
            # Wait for authentication to complete (shorter timeout)
            logger.info("Waiting for authentication completion...")
            max_wait_time = 30  # Reduced from 60 seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = self.driver.current_url
                
                # Check for successful login indicators
                if "quora.com" in current_url and "login" not in current_url.lower():
                    # Additional check: try to find user-specific elements
                    try:
                        user_elements = self.driver.find_elements(By.CSS_SELECTOR, ".header_login_text_name, .header_user_menu, [data-testid='user-menu']")
                        if user_elements:
                            logger.info("Successfully authenticated and redirected to Quora")
                            self.cookies = self.driver.get_cookies()
                            self.authenticated = True
                            return True
                    except:
                        pass
                
                # Check if we're on Google OAuth pages
                if "accounts.google.com" in current_url:
                    logger.info("On Google authentication page - waiting for completion...")
                
                time.sleep(2)
            
            # If we reach here, authentication might have completed but we're not sure
            logger.warning("Authentication timeout reached")
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
        # Check if this is a Selenium-only request (processing mode)
        if request.meta.get('use_selenium', False):
            logger.info("Skipping HTTP request - using Selenium directly")
            # Return a fake response since we'll handle everything in Selenium
            return HtmlResponse(
                url=request.url,
                body=b'<html><body>Selenium will handle this</body></html>',
                encoding='utf-8'
            )
        
        # For collection mode HTTP requests, ensure authentication and add cookies
        if not self.authenticated:
            if not self.driver:
                self.setup_driver()
            
            if not self.authenticate_with_google():
                logger.error("Authentication failed, cannot proceed")
                return None
        
        # Add cookies to request for authenticated access
        if self.cookies:
            cookie_dict = {cookie['name']: cookie['value'] for cookie in self.cookies}
            request.cookies.update(cookie_dict)
            
            # Add additional headers to make requests look more like a real browser
            request.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            })
            
            logger.debug(f"Added {len(cookie_dict)} cookies to request for {request.url}")
        
        return None
    
    def spider_closed(self, spider):
        """Clean up when spider closes"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed") 