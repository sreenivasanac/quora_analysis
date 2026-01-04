import os
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapy.http import HtmlResponse
from scrapy.exceptions import NotConfigured
from .chrome_driver_manager import get_chrome_manager

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware to handle Google OAuth authentication for Quora"""
    
    def __init__(self, email=None):
        self.email = email or os.getenv('GOOGLE_EMAIL', 'sreenivasan.ac92@gmail.com')
        if not self.email:
            raise NotConfigured("GOOGLE_EMAIL environment variable is required")

        self.chrome_manager = get_chrome_manager()
        self.cookies = None
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            email=crawler.settings.get('GOOGLE_EMAIL')
        )
    

    def authenticate_with_google(self):
        # TODO make this more robust, cleaner, and cleanup the code
        """Perform Google OAuth authentication for Quora"""
        if self.chrome_manager.is_authenticated():
            return True

        # Setup driver first if not already done
        if not self.chrome_manager.setup_driver():
            logger.error("Failed to setup Chrome driver")
            return False

        driver = self.chrome_manager.get_driver()

        try:
            logger.info("Starting Google OAuth authentication for Quora")

            # Check if already logged
            # Navigate to Quora main page to check authentication
            driver.get("https://www.quora.com/")

            # Check authentication through chrome_manager
            if self.chrome_manager.check_authentication():
                self.cookies = driver.get_cookies()
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
                        google_login = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        google_login = WebDriverWait(driver, 10).until(
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
                logger.info("Current page title: " + driver.title)
                logger.info("Current URL: " + driver.current_url)

                # Maybe we're already logged in but the check failed
                logger.warning("Assuming already logged in and proceeding...")
                self.cookies = driver.get_cookies()
                return True
            
            # Check if we're on Google OAuth page accounts.google.com
            current_url = driver.current_url
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
                                account_element = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            else:
                                # CSS selector
                                account_element = WebDriverWait(driver, 5).until(
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
                current_url = driver.current_url
                
                # Check for successful login indicators
                if "quora.com" in current_url and "login" not in current_url.lower():
                    # Additional check: try to find user-specific elements
                    is_authenticated = self.chrome_manager.check_authentication()
                    if is_authenticated:
                        self.cookies = driver.get_cookies()
                        return True
            
            current_url = driver.current_url
            logger.info(f"Current URL: {current_url}")
            
            # Try to proceed anyway - maybe we're logged in
            if "quora.com" in current_url:
                logger.warning("Assuming authentication successful and proceeding...")
                self.cookies = driver.get_cookies()
                return True
            else:
                logger.error("Authentication appears to have failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to authenticate with Google: {e}")
            
            # Try to proceed anyway in case we're already logged in
            try:
                current_url = driver.current_url
                if "quora.com" in current_url:
                    logger.warning("Exception occurred but still on Quora - attempting to proceed...")
                    self.cookies = driver.get_cookies()
                    return True
            except:
                pass
                
            return False
    
    def process_request(self, request, spider):
        """Process request with authentication if needed"""
        # Check if this is a Selenium-only request (no HTTP needed)
        if request.meta.get('use_selenium', False):
            logger.info("Skipping HTTP request - using Selenium directly")
            # Return a fake response since we'll handle everything in Selenium
            return HtmlResponse(
                url=request.url,
                body=b'<html><body>Selenium will handle this</body></html>',
                encoding='utf-8',
                request=request
            )
        
        # For regular HTTP requests, ensure authentication
        if not self.chrome_manager.is_authenticated():
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
        self.chrome_manager.cleanup()
        logger.info("Chrome driver closed") 