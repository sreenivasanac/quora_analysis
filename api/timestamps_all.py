from http.server import BaseHTTPRequestHandler
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

# Add the project root to Python path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import get_all_timestamps
from utils.timezone_utils import convert_to_timezone, TIMEZONES

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            timezone_name = query_params.get('timezone', ['IST'])[0]
            if timezone_name not in TIMEZONES:
                timezone_name = 'IST'

            # Get data from database
            results = get_all_timestamps()

            # Convert to target timezone
            timestamps = []
            for row in results:
                timestamp = row['post_timestamp_parsed']
                converted = convert_to_timezone(timestamp, timezone_name)
                if converted:
                    timestamps.append(converted.isoformat())

            response_data = {
                'success': True,
                'timestamps': timestamps,
                'count': len(timestamps),
                'timezone': timezone_name
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        except Exception as e:
            error_response = {
                'success': False,
                'error': str(e)
            }

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()