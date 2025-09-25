from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

app = Flask(__name__)
CORS(app)

# Timezone mappings
TIMEZONES = {
    'IST': 'Asia/Kolkata',      # UTC+5:30
    'CST': 'Asia/Shanghai',     # UTC+8:00
    'PST': 'America/Los_Angeles', # UTC-8:00 (varies with DST)
    'EST': 'America/New_York'    # UTC-5:00 (varies with DST)
}

def get_db_connection():
    """Create and return a database connection"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return psycopg2.connect(database_url)

def convert_to_timezone(timestamp, target_tz_name):
    """Convert timestamp to target timezone"""
    if timestamp is None:
        return None

    target_tz = pytz.timezone(TIMEZONES.get(target_tz_name, 'Asia/Kolkata'))

    # If timestamp is naive, assume it's in UTC
    if timestamp.tzinfo is None:
        timestamp = pytz.UTC.localize(timestamp)

    # Convert to target timezone
    return timestamp.astimezone(target_tz)

@app.route('/api/timestamps', methods=['GET'])
def get_timestamps():
    """
    Get timestamps for a specific date range
    Query params:
    - start_date: Start of the week (ISO format)
    - end_date: End of the week (ISO format)
    - timezone: One of IST, CST, PST, EST (default: IST)
    """
    try:
        # Get query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        timezone_name = request.args.get('timezone', 'IST')

        if timezone_name not in TIMEZONES:
            timezone_name = 'IST'

        # Parse dates
        if start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            # Default to current week
            now = datetime.now(pytz.UTC)
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Query timestamps in the range
        query = """
            SELECT post_timestamp_parsed
            FROM quora_answers
            WHERE post_timestamp_parsed IS NOT NULL
            AND post_timestamp_parsed >= %s
            AND post_timestamp_parsed < %s
            ORDER BY post_timestamp_parsed
        """

        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()

        # Convert timestamps to target timezone and format
        timestamps = []
        for row in results:
            timestamp = row['post_timestamp_parsed']
            converted = convert_to_timezone(timestamp, timezone_name)
            if converted:
                timestamps.append({
                    'datetime': converted.isoformat(),
                    'day': converted.strftime('%A'),
                    'hour': converted.hour,
                    'minute': converted.minute,
                    'date': converted.strftime('%Y-%m-%d')
                })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'timestamps': timestamps,
            'count': len(timestamps),
            'timezone': timezone_name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """
    Get overall statistics about the timestamps
    Query params:
    - timezone: One of IST, CST, PST, EST (default: IST)
    """
    try:
        timezone_name = request.args.get('timezone', 'IST')
        if timezone_name not in TIMEZONES:
            timezone_name = 'IST'

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

        # Get hourly distribution for the selected timezone
        cursor.execute("""
            SELECT post_timestamp_parsed
            FROM quora_answers
            WHERE post_timestamp_parsed IS NOT NULL
        """)
        all_timestamps = cursor.fetchall()

        # Calculate hourly distribution in the target timezone
        hourly_dist = {hour: 0 for hour in range(24)}
        weekday_dist = {day: 0 for day in range(7)}  # 0=Monday, 6=Sunday

        for row in all_timestamps:
            timestamp = row['post_timestamp_parsed']
            converted = convert_to_timezone(timestamp, timezone_name)
            if converted:
                hourly_dist[converted.hour] += 1
                weekday_dist[converted.weekday()] += 1

        # Find busiest hour and day
        busiest_hour = max(hourly_dist, key=hourly_dist.get)
        busiest_day = max(weekday_dist, key=weekday_dist.get)

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        cursor.close()
        conn.close()

        # Convert earliest and latest to target timezone
        earliest = convert_to_timezone(date_range['earliest'], timezone_name) if date_range['earliest'] else None
        latest = convert_to_timezone(date_range['latest'], timezone_name) if date_range['latest'] else None

        return jsonify({
            'success': True,
            'stats': {
                'total_count': total_count,
                'earliest_date': earliest.isoformat() if earliest else None,
                'latest_date': latest.isoformat() if latest else None,
                'busiest_hour': busiest_hour,
                'busiest_day': days[busiest_day],
                'hourly_distribution': hourly_dist,
                'weekday_distribution': {days[i]: count for i, count in weekday_dist.items()},
                'timezone': timezone_name
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/timestamps/all', methods=['GET'])
def get_all_timestamps():
    """
    Get all timestamps with minimal processing (for initial load or caching)
    Query params:
    - timezone: One of IST, CST, PST, EST (default: IST)
    """
    try:
        timezone_name = request.args.get('timezone', 'IST')
        if timezone_name not in TIMEZONES:
            timezone_name = 'IST'

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get all timestamps
        cursor.execute("""
            SELECT post_timestamp_parsed
            FROM quora_answers
            WHERE post_timestamp_parsed IS NOT NULL
            ORDER BY post_timestamp_parsed
        """)
        results = cursor.fetchall()

        # Convert to target timezone
        timestamps = []
        for row in results:
            timestamp = row['post_timestamp_parsed']
            converted = convert_to_timezone(timestamp, timezone_name)
            if converted:
                timestamps.append(converted.isoformat())

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'timestamps': timestamps,
            'count': len(timestamps),
            'timezone': timezone_name
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Quora Timestamp Visualization API'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)