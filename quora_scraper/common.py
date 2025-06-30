#!/usr/bin/env python3
"""
Common utilities for Quora scraper
"""

import logging
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


def check_quora_authentication(driver):
    """
    Check if user is authenticated to Quora by looking for logged-in indicators
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if authenticated, False otherwise
    """
    try:
        # Look for elements that indicate we're already logged in
        logged_in_indicators = [
            "img[alt*='Profile photo for']",  # Profile photo in header
            ".puppeteer_test_add_question_button",  # Add question button (only visible when logged in)
            "a[aria-label='Account menu']",  # Account menu button
            "a[href*='/notifications']",  # Notifications link
            "input[placeholder='Search Quora']",  # Search input (different when logged in)
            ".q-image[alt*='Profile photo']"  # Alternative profile photo selector
        ]
        
        for indicator in logged_in_indicators:
            try:
                element = driver.find_element(By.CSS_SELECTOR, indicator)
                if element and element.is_displayed():
                    logger.info(f"Already authenticated to Quora (found: {indicator})")
                    return True
            except:
                continue
        
        logger.warning("Not authenticated to Quora - no login indicators found")
        return False
        
    except Exception as e:
        logger.error(f"Error checking authentication status: {e}")
        return False
