import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Default SQLite database path
DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quora_answers.db")


def dict_factory(cursor, row):
    """Convert SQLite row to dictionary"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_db_connection():
    """Create and return a database connection"""
    database_path = os.getenv('SQLITE_DB_PATH') or DEFAULT_SQLITE_PATH
    conn = sqlite3.connect(database_path)
    conn.row_factory = dict_factory
    return conn


def parse_timestamp(ts_str):
    """Parse timestamp string to datetime object"""
    if not ts_str:
        return None
    try:
        # Handle ISO format with timezone
        if '+' in ts_str or ts_str.endswith('Z'):
            # Remove timezone for simplicity (SQLite stores as string)
            ts_str = ts_str.replace('Z', '+00:00')
            return datetime.fromisoformat(ts_str.replace(' ', 'T'))
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def get_timestamps_for_date_range(start_date_ist, end_date_ist):
    """Get timestamps with question text and URLs for a date range"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT post_timestamp_parsed, question_text, answered_question_url
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
        AND post_timestamp_parsed >= ?
        AND post_timestamp_parsed < ?
        ORDER BY post_timestamp_parsed
    """

    # Convert dates to strings for SQLite comparison
    start_str = str(start_date_ist.replace(tzinfo=None))
    end_str = str(end_date_ist.replace(tzinfo=None))
    
    cursor.execute(query, (start_str, end_str))
    results = cursor.fetchall()

    # Parse timestamps back to datetime objects
    for row in results:
        row['post_timestamp_parsed'] = parse_timestamp(row['post_timestamp_parsed'])

    cursor.close()
    conn.close()

    return results


def get_statistics():
    """Get overall statistics about timestamps"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) as total FROM quora_answers WHERE post_timestamp_parsed IS NOT NULL")
    total_count = cursor.fetchone()['total']

    # Get date range
    cursor.execute("""
        SELECT
            MIN(post_timestamp_parsed) as earliest,
            MAX(post_timestamp_parsed) as latest
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
    """)
    date_range = cursor.fetchone()

    # Get all timestamps for distribution calculations
    cursor.execute("""
        SELECT post_timestamp_parsed
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
    """)
    all_timestamps = cursor.fetchall()

    # Parse timestamps
    for row in all_timestamps:
        row['post_timestamp_parsed'] = parse_timestamp(row['post_timestamp_parsed'])

    cursor.close()
    conn.close()

    return {
        'total_count': total_count,
        'earliest': parse_timestamp(date_range['earliest']),
        'latest': parse_timestamp(date_range['latest']),
        'all_timestamps': all_timestamps
    }


def get_all_timestamps():
    """Get all timestamps with minimal processing"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT post_timestamp_parsed
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
        ORDER BY post_timestamp_parsed
    """)
    results = cursor.fetchall()

    # Parse timestamps
    for row in results:
        row['post_timestamp_parsed'] = parse_timestamp(row['post_timestamp_parsed'])

    cursor.close()
    conn.close()

    return results
