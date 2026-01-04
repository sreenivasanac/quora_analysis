#!/usr/bin/env python3
"""
Migration script to export PostgreSQL data to SQLite.
Run this script to create a SQLite database with all data from PostgreSQL.

Usage:
    python migrate_to_sqlite.py
    python migrate_to_sqlite.py --db-url "postgresql://user:pass@host:port/dbname"
"""
import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB_PATH = "quora_answers.db"


def get_database_url():
    """Get database URL from command line args or environment"""
    # Check for --db-url argument
    for i, arg in enumerate(sys.argv):
        if arg == "--db-url" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    
    # Fall back to environment variable
    return os.getenv('DATABASE_URL')


def create_sqlite_schema(sqlite_conn):
    """Create the SQLite schema matching PostgreSQL structure"""
    cursor = sqlite_conn.cursor()
    
    # SQLite schema - note differences from PostgreSQL:
    # - INTEGER PRIMARY KEY AUTOINCREMENT instead of SERIAL
    # - TEXT for timestamps (SQLite doesn't have native TIMESTAMP WITH TIME ZONE)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quora_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_url TEXT,
            answered_question_url TEXT UNIQUE,
            question_text TEXT,
            answer_content TEXT,
            revision_link TEXT,
            post_timestamp_raw TEXT,
            post_timestamp_parsed TEXT
        )
    """)
    
    # Create index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_answered_question_url 
        ON quora_answers(answered_question_url)
    """)
    
    sqlite_conn.commit()
    print("SQLite schema created successfully")


def migrate_data(pg_conn, sqlite_conn):
    """Migrate all data from PostgreSQL to SQLite"""
    pg_cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Fetch all data from PostgreSQL
    pg_cursor.execute("""
        SELECT id, question_url, answered_question_url, question_text, 
               answer_content, revision_link, post_timestamp_raw, post_timestamp_parsed
        FROM quora_answers
        ORDER BY id
    """)
    
    rows = pg_cursor.fetchall()
    print(f"Fetched {len(rows)} rows from PostgreSQL")
    
    # Insert into SQLite
    insert_sql = """
        INSERT OR REPLACE INTO quora_answers 
        (id, question_url, answered_question_url, question_text, 
         answer_content, revision_link, post_timestamp_raw, post_timestamp_parsed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        values = [
            (
                row['id'],
                row['question_url'],
                row['answered_question_url'],
                row['question_text'],
                row['answer_content'],
                row['revision_link'],
                row['post_timestamp_raw'],
                str(row['post_timestamp_parsed']) if row['post_timestamp_parsed'] else None
            )
            for row in batch
        ]
        sqlite_cursor.executemany(insert_sql, values)
        sqlite_conn.commit()
        print(f"Migrated {min(i+batch_size, len(rows))}/{len(rows)} rows...")
    
    # Verify count
    sqlite_cursor.execute("SELECT COUNT(*) FROM quora_answers")
    count = sqlite_cursor.fetchone()[0]
    print(f"\nMigration complete! SQLite database has {count} rows")
    
    pg_cursor.close()


def main():
    # Get PostgreSQL connection
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL is required")
        print("Options:")
        print("  1. Set DATABASE_URL in your .env file")
        print("  2. Pass via command line: python migrate_to_sqlite.py --db-url 'postgresql://...'")
        print("\nExample for Supabase:")
        print("  python migrate_to_sqlite.py --db-url 'postgresql://postgres.xxx:PASSWORD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'")
        return
    
    print(f"Connecting to PostgreSQL...")
    
    try:
        pg_conn = psycopg2.connect(database_url)
        print("Connected to PostgreSQL")
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return
    
    # Remove existing SQLite database if it exists
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        print(f"Removed existing {SQLITE_DB_PATH}")
    
    # Create SQLite connection
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    print(f"Created new SQLite database: {SQLITE_DB_PATH}")
    
    try:
        # Create schema
        create_sqlite_schema(sqlite_conn)
        
        # Migrate data
        migrate_data(pg_conn, sqlite_conn)
        
        print(f"\nSQLite database created at: {os.path.abspath(SQLITE_DB_PATH)}")
        print("\nTo use SQLite, update your .env file:")
        print(f"  SQLITE_DB_PATH={os.path.abspath(SQLITE_DB_PATH)}")
        
    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
