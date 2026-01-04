#!/usr/bin/env python3
"""
Database setup script for Quora Answer Scraper
Creates the necessary database tables and indexes
"""

import os
import sys
from dotenv import load_dotenv
from quora_scraper.database_sqlite import DatabaseManager

def setup_database():
    """Setup the PostgreSQL database with required tables"""
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set!")
        print("Please set it in your .env file or environment.")
        print("Example: DATABASE_URL=postgresql://username:password@localhost:5432/quora_analysis1")
        sys.exit(1)
    
    try:
        print("Setting up PostgreSQL database...")
        
        # Initialize database manager
        db_manager = DatabaseManager(database_url)
        db_manager.connect()
        
        # Create tables
        db_manager.create_tables()
        
        # Check current state
        answer_count = db_manager.get_answer_count()
        print(f"Database setup complete!")
        print(f"Current answer count in database: {answer_count}")
        
        # Disconnect
        db_manager.disconnect()
        
        print("\nDatabase is ready for scraping!")
        
    except Exception as e:
        print(f"ERROR: Failed to setup database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database() 