#!/usr/bin/env python3
"""
Main script to run the Quora Answer Scraper
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quora_scraper.spiders.quora_profile_spider import QuoraProfileSpider
from quora_scraper.answer_processor import run_answer_processor

def setup_logging(log_file='quora_scraper.log'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['DATABASE_URL', 'GOOGLE_EMAIL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        print("See .env.example for reference.")
        sys.exit(1)

def run_collector():
    """Run the Quora answer URL collector"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging for collection
    setup_logging('quora_scraper.log')
    
    # Check environment
    check_environment()
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Quora Answer URL Collection for Kanthaswamy Balasubramaniam")
        
        # Get Scrapy settings
        settings = get_project_settings()
        settings.setmodule('quora_scraper.settings')
        
        # Override settings from environment if provided
        if os.getenv('SCRAPY_LOG_LEVEL'):
            settings.set('LOG_LEVEL', os.getenv('SCRAPY_LOG_LEVEL'))
        
        if os.getenv('SCRAPY_DOWNLOAD_DELAY'):
            settings.set('DOWNLOAD_DELAY', float(os.getenv('SCRAPY_DOWNLOAD_DELAY')))
        
        # Create and start the crawler process
        process = CrawlerProcess(settings)
        process.crawl(QuoraProfileSpider)
        
        logger.info("Starting URL collection process...")
        process.start()  # This will block until crawling is finished
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error running collector: {e}")
        return False

def run_processor():
    """Run the Quora answer data processor"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging for processing
    setup_logging('quora_process.log')
    
    # Check environment
    check_environment()
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Quora Answer Data Processing for existing database entries")
        
        # Run the answer processor
        success = run_answer_processor()
        
        if success:
            logger.info("Answer processing completed successfully")
        else:
            logger.error("Answer processing failed")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error running processor: {e}")
        return False

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Quora Answer Scraper for Kanthaswamy Balasubramaniam',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python run_scraper.py                    # Collect new answer URLs (default)
        python run_scraper.py --mode collect     # Collect new answer URLs  
        python run_scraper.py --mode process     # Process existing URLs and populate data
                """
            )
    
    parser.add_argument(
        '--mode',
        choices=['collect', 'process'],
        default='collect',
        help='Scraper mode: "collect" to gather answer URLs, "process" to populate existing entries (default: collect)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Quora Answer Scraper for Kanthaswamy Balasubramaniam")
    print("=" * 70)
    print()
    
    if args.mode == 'collect':
        print("MODE: Answer URL Collection")
        print("This will scroll through Kanthaswamy's answer page and collect all answer URLs.")
        print("New URLs will be saved to the database.")
        print("Log file: quora_scraper.log")
    else:
        print("MODE: Answer Data Processing") 
        print("This will process existing answer URLs in the database and populate:")
        print("- Question URL and text")
        print("- Answer content (converted to Markdown)")
        print("- Revision links and timestamps")
        print("Log file: quora_process.log")
    
    print()
    
    # Check if database setup has been run
    if not os.path.exists('quora_scraper.log') and not os.path.exists('quora_process.log'):
        print("NOTICE: This appears to be the first run.")
        print("Make sure you have:")
        print("1. Set up your PostgreSQL database")
        print("2. Created a .env file with DATABASE_URL and GOOGLE_EMAIL")
        print("3. Run 'python setup_database.py' to initialize the database")
        print()
        
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting. Please complete the setup first.")
            sys.exit(0)
    
    # Show additional info for process mode
    if args.mode == 'process':
        print("IMPORTANT NOTES for Processing Mode:")
        print("AUTHENTICATION REQUIREMENT:")
        print("- Processing mode requires an authenticated Chrome session")
        print("- If you haven't run the collector recently, you may need to:")
        print("  1. Start Chrome with the command:")
        print("     exec arch -arm64 /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \\")
        print("       --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug_profile")
        print("  2. Authenticate to Quora manually in the browser")
        print("  3. Then run the processor")
        print()
        
        response = input("Continue with processing mode? (y/N): ")
        if response.lower() != 'y':
            print("Exiting.")
            sys.exit(0)
    
    # Run the appropriate mode
    if args.mode == 'collect':
        success = run_collector()
    else:
        success = run_processor()
    
    if success:
        print(f"\n{args.mode.title()} mode completed successfully!")
    else:
        print(f"\n{args.mode.title()} mode failed or was interrupted.")
        sys.exit(1)

if __name__ == "__main__":
    main() 