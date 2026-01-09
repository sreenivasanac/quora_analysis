#!/usr/bin/env python3
"""
Test script for the Quora Answer Processor to verify CDP connection and authentication
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quora_scraper.answer_processor import QuoraAnswerProcessor
from quora_scraper.chrome_driver_manager import ChromeDriverManager

def setup_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def test_processor_connection():
    """Test the processor's ability to connect via CDP and check authentication"""
    load_dotenv()
    setup_logging()
    
    logger = logging.getLogger(__name__)
    
    print("=" * 70)
    print("Testing Quora Answer Processor CDP Connection & Authentication")
    print("=" * 70)
    print()
    
    print("This test will:")
    print("1. Try to connect to existing Chrome instance via CDP (port 9223)")
    print("2. Check if authenticated to Quora")
    print("3. Display current browser state")
    print()

    # Create ChromeDriverManager with port 9223 for processing mode
    chrome_manager = ChromeDriverManager()
    chrome_manager.debug_port = 9223

    # Create processor and override its chrome_manager
    processor = QuoraAnswerProcessor()
    processor.chrome_manager = chrome_manager

    try:
        print("Step 1: Setting up Chrome driver with CDP connection on port 9223...")
        # The processor initializes chrome_manager in __init__
        if processor.chrome_manager.setup_driver():
            print("✓ Successfully connected to Chrome via CDP")

            driver = processor.chrome_manager.get_driver()

            # Get current page info
            current_url = driver.current_url
            current_title = driver.title
            print(f"Current page: {current_title}")
            print(f"Current URL: {current_url}")
            print()

            print("Step 2: Checking authentication status...")
            if processor.chrome_manager.is_authenticated():
                print("✓ Already authenticated to Quora")
            else:
                print("✗ Not authenticated to Quora")
                print("Please authenticate manually in the browser and run this test again")

            print()
            print("Step 3: Testing navigation to a Quora answer page...")
            test_url = "https://www.quora.com/profile/Kanthaswamy-Balasubramaniam/answers"
            driver.get(test_url)

            import time
            time.sleep(3)

            final_url = driver.current_url
            final_title = driver.title

            print(f"Navigated to: {final_title}")
            print(f"Final URL: {final_url}")

            if "profile" in final_url and "Kanthaswamy" in final_url:
                print("✓ Successfully accessed Kanthaswamy's profile page")
                print("✓ Authentication appears to be working")
            else:
                print("✗ Could not access profile page - authentication may be required")

        else:
            print("✗ Failed to connect to Chrome")
            print("Make sure Chrome is running with remote debugging:")
            print("python start_chrome_debug.py")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print("✗ Test failed - see error above")
        
    finally:
        if processor.chrome_manager:
            print("\nCleaning up...")
            processor.chrome_manager.cleanup()
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_processor_connection() 