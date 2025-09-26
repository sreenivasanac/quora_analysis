#!/usr/bin/env python3
"""
Test database connectivity for both local and production environments
"""

import os
from dotenv import load_dotenv
from utils.database import get_db_connection

def test_database():
    load_dotenv()

    try:
        print("🔍 Testing database connection...")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT COUNT(*) FROM quora_answers WHERE post_timestamp_parsed IS NOT NULL")
        count = cursor.fetchone()[0]

        print(f"✅ Database connection successful!")
        print(f"📊 Found {count} records with parsed timestamps")

        # Test sample data
        cursor.execute("SELECT question_text FROM quora_answers WHERE question_text IS NOT NULL LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"📄 Sample question: {sample[0][:100]}...")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database()
    exit(0 if success else 1)