from http.server import BaseHTTPRequestHandler
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

# Add the project root to Python path so we can import utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import get_statistics
from utils.timezone_utils import convert_to_timezone, calculate_distributions, TIMEZONES

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
            stats_data = get_statistics()

            # Calculate distributions in the target timezone
            distributions = calculate_distributions(stats_data['all_timestamps'], timezone_name)

            # Convert earliest and latest to target timezone
            earliest = convert_to_timezone(stats_data['earliest'], timezone_name) if stats_data['earliest'] else None
            latest = convert_to_timezone(stats_data['latest'], timezone_name) if stats_data['latest'] else None

            response_data = {
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