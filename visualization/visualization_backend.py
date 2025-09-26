from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import get_timestamps_for_date_range, get_statistics, get_all_timestamps
from utils.timezone_utils import (
    convert_to_timezone, get_date_range_for_timezone,
    calculate_distributions, TIMEZONES
)

load_dotenv()

app = Flask(__name__)
CORS(app)

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

        # Get date range using shared utility
        start_date, end_date, start_date_ist, end_date_ist = get_date_range_for_timezone(
            start_date_str, end_date_str, timezone_name
        )

        # Get data from database using shared utility
        results = get_timestamps_for_date_range(start_date_ist, end_date_ist)

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
                    'date': converted.strftime('%Y-%m-%d'),
                    'question_text': row['question_text'] or 'No question text',
                    'answer_url': row['answered_question_url'] or '#'
                })

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
def get_stats():
    """
    Get overall statistics about the timestamps
    Query params:
    - timezone: One of IST, CST, PST, EST (default: IST)
    """
    try:
        timezone_name = request.args.get('timezone', 'IST')
        if timezone_name not in TIMEZONES:
            timezone_name = 'IST'

        # Get data from database using shared utility
        stats_data = get_statistics()

        # Calculate distributions in the target timezone using shared utility
        distributions = calculate_distributions(stats_data['all_timestamps'], timezone_name)

        # Convert earliest and latest to target timezone
        earliest = convert_to_timezone(stats_data['earliest'], timezone_name) if stats_data['earliest'] else None
        latest = convert_to_timezone(stats_data['latest'], timezone_name) if stats_data['latest'] else None

        return jsonify({
            'success': True,
            'stats': {
                'total_count': stats_data['total_count'],
                'earliest_date': earliest.isoformat() if earliest else None,
                'latest_date': latest.isoformat() if latest else None,
                'busiest_hour': distributions['busiest_hour'],
                'busiest_day': distributions['busiest_day'],
                'hourly_distribution': distributions['hourly_distribution'],
                'weekday_distribution': distributions['weekday_distribution'],
                'timezone': timezone_name
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/timestamps/all', methods=['GET'])
def get_all_timestamps_route():
    """
    Get all timestamps with minimal processing (for initial load or caching)
    Query params:
    - timezone: One of IST, CST, PST, EST (default: IST)
    """
    try:
        timezone_name = request.args.get('timezone', 'IST')
        if timezone_name not in TIMEZONES:
            timezone_name = 'IST'

        # Get data from database using shared utility
        results = get_all_timestamps()

        # Convert to target timezone
        timestamps = []
        for row in results:
            timestamp = row['post_timestamp_parsed']
            converted = convert_to_timezone(timestamp, timezone_name)
            if converted:
                timestamps.append(converted.isoformat())

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