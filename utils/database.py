import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return psycopg2.connect(database_url)

def get_timestamps_for_date_range(start_date_ist, end_date_ist):
    """Get timestamps with question text and URLs for a date range"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
        SELECT post_timestamp_parsed, question_text, answered_question_url
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
        AND post_timestamp_parsed >= %s
        AND post_timestamp_parsed < %s
        ORDER BY post_timestamp_parsed
    """

    cursor.execute(query, (start_date_ist.replace(tzinfo=None), end_date_ist.replace(tzinfo=None)))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return results

def get_statistics():
    """Get overall statistics about timestamps"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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

    cursor.close()
    conn.close()

    return {
        'total_count': total_count,
        'earliest': date_range['earliest'],
        'latest': date_range['latest'],
        'all_timestamps': all_timestamps
    }

def get_all_timestamps():
    """Get all timestamps with minimal processing"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT post_timestamp_parsed
        FROM quora_answers
        WHERE post_timestamp_parsed IS NOT NULL
        ORDER BY post_timestamp_parsed
    """)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return results