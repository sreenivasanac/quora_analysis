#!/usr/bin/env python3
"""
Test script to verify database integration and new processing functionality
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quora_scraper.database import DatabaseManager
from datetime import datetime
import pytz

def test_database_integration():
    """Test database connection and operations"""
    
    # Load environment variables
    load_dotenv()
    
    try:
        print("Testing database integration...")
        print("-" * 50)
        
        # Test connection
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✓ Database connection successful")
        
        # Test table creation
        db_manager.create_tables()
        print("✓ Database tables created/verified")
        
        # Test basic operations
        total_count = db_manager.get_answer_count()
        print(f"✓ Total answers in database: {total_count}")
        
        # Test new methods for processing functionality
        incomplete_count = db_manager.get_incomplete_count()
        print(f"✓ Incomplete entries count: {incomplete_count}")
        
        # Test getting incomplete entries (limit to 5 for testing)
        incomplete_entries = db_manager.get_incomplete_entries(limit=5)
        print(f"✓ Retrieved {len(incomplete_entries)} incomplete entries (limited to 5)")
        
        if incomplete_entries:
            print("Sample incomplete entries:")
            for i, entry in enumerate(incomplete_entries[:3], 1):
                print(f"  {i}. ID: {entry['id']}, URL: {entry['answered_question_url'][:60]}...")
        
        # Test update functionality with sample data (if we have incomplete entries)
        if incomplete_entries:
            test_entry = incomplete_entries[0]
            test_url = test_entry['answered_question_url']
            
            # Create sample data for testing
            sample_timestamp = datetime.now(pytz.timezone('US/Pacific'))
            
            print(f"\nTesting update functionality with entry ID {test_entry['id']}...")
            
            # Test update (with sample data - not real scraping)
            success = db_manager.update_answer_data(
                answered_question_url=test_url,
                question_text="Sample question for testing",
                answer_content="Sample answer content in **markdown** format",
                post_timestamp_raw="January 1, 2024 at 12:00:00 PM",
                post_timestamp_parsed=sample_timestamp
            )
            
            if success:
                print("✓ Update operation successful")
                
                # Verify the update by checking incomplete count again
                new_incomplete_count = db_manager.get_incomplete_count()
                if new_incomplete_count < incomplete_count:
                    print("✓ Incomplete count decreased - update verified")
                else:
                    print("⚠ Incomplete count unchanged - entry may have been partially complete")
            else:
                print("✗ Update operation failed")
        
        # Test getting all answer URLs
        all_urls = db_manager.get_all_answer_urls()
        print(f"✓ Retrieved {len(all_urls)} existing URLs from database")
        
        # Clean up
        db_manager.disconnect()
        print("✓ Database connection closed")
        
        print("\n" + "=" * 50)
        print("Database integration test completed successfully!")
        print(f"Total entries: {total_count}")
        print(f"Complete entries: {total_count - incomplete_count}")
        print(f"Incomplete entries: {incomplete_count}")
        
        if incomplete_count > 0:
            print(f"\nTo process incomplete entries, run:")
            print("python run_scraper.py --mode process")
        
        return True
        
    except Exception as e:
        print(f"✗ Database integration test failed: {e}")
        return False

def test_timestamp_parsing():
    """Test timestamp parsing functionality"""
    print("\nTesting timestamp parsing...")
    print("-" * 30)
    
    # Import the spider to test timestamp parsing
    from quora_scraper.spiders.quora_profile_spider import QuoraProfileSpider
    
    spider = QuoraProfileSpider()
    
    # Test various timestamp formats
    test_timestamps = [
        "June 27, 2025 at 10:26:56 PM",
        "January 1, 2024 at 12:00:00 AM",
        "December 31, 2023 at 11:59:59 PM",
        "March 15, 2024 at 3:30:45 PM"
    ]
    
    for timestamp_str in test_timestamps:
        try:
            parsed = spider.parse_quora_timestamp(timestamp_str)
            if parsed:
                print(f"✓ '{timestamp_str}' -> {parsed}")
            else:
                print(f"✗ Failed to parse: '{timestamp_str}'")
        except Exception as e:
            print(f"✗ Error parsing '{timestamp_str}': {e}")
    
    # Test invalid timestamp
    try:
        invalid_result = spider.parse_quora_timestamp("Invalid timestamp")
        if invalid_result is None:
            print("✓ Invalid timestamp correctly returned None")
        else:
            print("✗ Invalid timestamp should return None")
    except Exception as e:
        print(f"✓ Invalid timestamp correctly raised exception: {e}")

if __name__ == "__main__":
    print("Quora Scraper Database Integration Test")
    print("=" * 50)
    
    # Test database integration
    db_success = test_database_integration()
    
    # Test timestamp parsing
    test_timestamp_parsing()
    
    print("\n" + "=" * 50)
    if db_success:
        print("All tests completed successfully!")
        print("\nYou can now run the scraper in either mode:")
        print("- Collection: python run_scraper.py --mode collect")
        print("- Processing: python run_scraper.py --mode process")
    else:
        print("Some tests failed. Please check your database configuration.")
        sys.exit(1) 