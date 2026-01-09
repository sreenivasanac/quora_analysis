#!/usr/bin/env python3
"""
API Testing Script for Local and Production environments
Usage: python test_api.py [local|production] [vercel-url]
"""

import sys
import requests
import json
from datetime import datetime, timedelta

def test_endpoints(base_url):
    """Test all API endpoints"""
    print(f"🧪 Testing API at: {base_url}")
    print("-" * 50)

    endpoints = [
        {
            "name": "Health Check",
            "url": f"{base_url}/api/health",
            "method": "GET"
        },
        {
            "name": "Stats (IST)",
            "url": f"{base_url}/api/stats?timezone=IST",
            "method": "GET"
        },
        {
            "name": "Current Week Timestamps",
            "url": f"{base_url}/api/timestamps?timezone=IST",
            "method": "GET"
        },
        {
            "name": "All Timestamps (first 5)",
            "url": f"{base_url}/api/timestamps/all?timezone=IST",
            "method": "GET"
        }
    ]

    results = []
    for endpoint in endpoints:
        try:
            print(f"Testing: {endpoint['name']}")
            response = requests.get(endpoint['url'], timeout=30)

            status = "✅ PASS" if response.status_code == 200 else "❌ FAIL"
            print(f"  Status: {response.status_code} - {status}")

            if response.status_code == 200:
                data = response.json()
                if endpoint['name'] == "All Timestamps (first 5)":
                    # Show only first 5 timestamps for brevity
                    if 'timestamps' in data:
                        data['timestamps'] = data['timestamps'][:5]
                        data['count_shown'] = f"Showing 5 of {data.get('count', 0)}"

                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
            else:
                print(f"  Error: {response.text[:100]}")

            results.append({
                'endpoint': endpoint['name'],
                'status': response.status_code,
                'success': response.status_code == 200
            })

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({
                'endpoint': endpoint['name'],
                'status': 'ERROR',
                'success': False
            })

        print()

    # Summary
    print("📊 Test Summary:")
    print("-" * 30)
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"Passed: {passed}/{total}")

    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        print(f"  {status_icon} {result['endpoint']} - {result['status']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_api.py [local|production] [vercel-url]")
        print("Examples:")
        print("  python test_api.py local")
        print("  python test_api.py production https://your-app.vercel.app")
        sys.exit(1)

    env = sys.argv[1].lower()

    if env == "local":
        base_url = "http://localhost:5000"
    elif env == "production":
        if len(sys.argv) < 3:
            print("Error: Production testing requires Vercel URL")
            print("Example: python test_api.py production https://your-app.vercel.app")
            sys.exit(1)
        base_url = sys.argv[2].rstrip('/')
    else:
        print("Error: Environment must be 'local' or 'production'")
        sys.exit(1)

    test_endpoints(base_url)

if __name__ == "__main__":
    main()