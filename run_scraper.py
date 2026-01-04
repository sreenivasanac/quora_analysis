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
from quora_scraper.parallel_answer_processor import run_parallel_processor

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
    required_vars = ['GOOGLE_EMAIL']
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

        # Configure Scrapy logging to suppress version info
        from scrapy import settings as scrapy_settings
        import scrapy.utils.log

        # Get Scrapy settings
        settings = get_project_settings()
        settings.setmodule('quora_scraper.settings')

        # Suppress all verbose Scrapy startup logging
        logging.getLogger('scrapy').setLevel(logging.ERROR)
        logging.getLogger('scrapy.utils.log').setLevel(logging.ERROR)
        logging.getLogger('scrapy.core.engine').setLevel(logging.ERROR)
        logging.getLogger('scrapy.addons').setLevel(logging.ERROR)
        logging.getLogger('scrapy.crawler').setLevel(logging.ERROR)
        logging.getLogger('scrapy.middleware').setLevel(logging.ERROR)
        logging.getLogger('asyncio').setLevel(logging.ERROR)
        logging.getLogger('scrapy.extensions').setLevel(logging.ERROR)
        logging.getLogger('scrapy.extensions.throttle').setLevel(logging.ERROR)
        logging.getLogger('scrapy.spidermiddlewares.httperror').setLevel(logging.ERROR)
        logging.getLogger('scrapy.downloadermiddlewares.cookies').setLevel(logging.ERROR)
        logging.getLogger('scrapy.statscollectors').setLevel(logging.ERROR)
        logging.getLogger('selenium').setLevel(logging.ERROR)
        logging.getLogger('selenium.webdriver.common.driver_finder').setLevel(logging.ERROR)
        logging.getLogger('selenium.webdriver.common.service').setLevel(logging.ERROR)
        logging.getLogger('quora_scraper.middlewares').setLevel(logging.WARNING)
        logging.getLogger('quora_scraper.chrome_driver_manager').setLevel(logging.WARNING)

        # Override settings from environment if provided
        if os.getenv('SCRAPY_LOG_LEVEL'):
            settings.set('LOG_LEVEL', os.getenv('SCRAPY_LOG_LEVEL'))

        if os.getenv('SCRAPY_DOWNLOAD_DELAY'):
            settings.set('DOWNLOAD_DELAY', float(os.getenv('SCRAPY_DOWNLOAD_DELAY')))

        # Create and start the crawler process with custom log configuration
        process = CrawlerProcess(settings, install_root_handler=False)
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

def run_processor(workers=None):
    """Run the Quora answer data processor

    Args:
        workers: Number of parallel workers (None for sequential, 1-5 for parallel)
    """
    # Load environment variables
    load_dotenv()

    # Setup logging for processing
    setup_logging('quora_process.log')

    # Check environment
    check_environment()

    logger = logging.getLogger(__name__)

    try:
        if workers and workers > 1:
            logger.info(f"Starting Parallel Quora Answer Processing with {workers} workers")
            # Run the parallel processor
            success = run_parallel_processor(num_workers=workers)
        else:
            logger.info("Starting Sequential Quora Answer Data Processing")
            # Run the sequential processor
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
        python run_scraper.py                         # Collect new answer URLs (default)
        python run_scraper.py --mode collect          # Collect new answer URLs
        python run_scraper.py --mode process          # Process existing URLs sequentially
        python run_scraper.py --mode process --workers 3   # Process with 3 parallel workers
        python run_scraper.py --mode process --workers 5   # Process with 5 parallel workers (max)
                """
            )
    
    parser.add_argument(
        '--mode',
        choices=['collect', 'process'],
        default='collect',
        help='Scraper mode: "collect" to gather answer URLs, "process" to populate existing entries (default: collect)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers for processing mode (1-5, default: sequential processing)'
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
        if args.workers and args.workers > 1:
            print(f"PARALLEL PROCESSING: {args.workers} workers")
            print(f"Chrome ports: {9223} - {9223 + args.workers - 1}")
        else:
            print("SEQUENTIAL PROCESSING: Single worker")
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
        print("- Processing mode requires authenticated Chrome session(s)")

        if args.workers and args.workers > 1:
            # Validate worker count
            if args.workers > 5:
                print(f"\nERROR: Maximum 5 workers allowed. You specified {args.workers}.")
                sys.exit(1)

            print(f"\nPARALLEL MODE: {args.workers} Chrome instances required")
            print("- If Chrome instances are not already running, they will be started automatically")
            print("- Ports to be used: ", end="")
            ports = [str(9223 + i) for i in range(args.workers)]
            print(", ".join(ports))
            print()
            print("To manually start Chrome instances (if needed):")
            print(f"  python start_parallel_chrome.py -n {args.workers}")
        else:
            print("\nSEQUENTIAL MODE: Single Chrome instance")
            print("- If not already running, start Chrome with:")
            print("  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \\")
            print("    --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug_profile")

        print("\nAuthenticate to Quora in each Chrome instance if not already logged in.")
        print()

        response = input("Continue with processing mode? (y/N): ")
        if response.lower() != 'y':
            print("Exiting.")
            sys.exit(0)
    
    # Run the appropriate mode
    if args.mode == 'collect':
        success = run_collector()
    else:
        success = run_processor(workers=args.workers)
    
    if success:
        print(f"\n{args.mode.title()} mode completed successfully!")
    else:
        print(f"\n{args.mode.title()} mode failed or was interrupted.")
        sys.exit(1)

if __name__ == "__main__":
    main() 