#!/usr/bin/env python3
"""
Helper script to start Chrome with remote debugging enabled.
Run this script to start Chrome in a mode that allows Selenium to connect to it.
"""

import platform
import subprocess
import sys
import time
import requests
import os

def start_chrome_with_debugging():
    """Start Chrome with remote debugging enabled"""
    debug_port = 9222
    
    # Check if Chrome is already running with debugging
    try:
        response = requests.get(f'http://localhost:{debug_port}/json', timeout=2)
        if response.status_code == 200:
            print(f"✅ Chrome is already running with remote debugging on port {debug_port}")
            print("You can now run your scraper - it will connect to this Chrome instance.")
            return True
    except requests.RequestException:
        pass
    
    print("Starting Chrome with remote debugging enabled...")
    
    try:
        is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
        
        if is_mac_arm:
            print("Detected Mac ARM architecture")
            chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        else:
            # For Intel Macs and other systems
            chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            if not os.path.exists(chrome_path):
                # Try common Chrome paths
                possible_paths = [
                    '/usr/bin/google-chrome',
                    '/usr/bin/chromium-browser',
                    'google-chrome'
                ]
                for path in possible_paths:
                    if os.path.exists(path) or subprocess.run(['which', path], 
                                                            capture_output=True).returncode == 0:
                        chrome_path = path
                        break
        
        if not os.path.exists(chrome_path):
            print(f"❌ Chrome not found at {chrome_path}")
            print("Please install Google Chrome or update the chrome_path in this script")
            return False
        
        # Start Chrome with remote debugging
        chrome_cmd = [
            chrome_path,
            f'--remote-debugging-port={debug_port}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
            '--disable-web-security',  # Sometimes needed for debugging
            '--user-data-dir=/tmp/chrome_debug_session'  # Use temporary profile
        ]
        
        print(f"Starting Chrome with command: {' '.join(chrome_cmd)}")
        process = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for Chrome to start
        print("Waiting for Chrome to start...")
        for i in range(10):
            time.sleep(1)
            try:
                response = requests.get(f'http://localhost:{debug_port}/json', timeout=2)
                if response.status_code == 200:
                    print(f"✅ Chrome started successfully with remote debugging on port {debug_port}")
                    print("🌐 You can now navigate to Quora.com in this Chrome window")
                    print("🔐 Log in to your account if needed")
                    print("🚀 Then run your scraper - it will connect to this Chrome instance")
                    print("\n📋 Chrome debugging info:")
                    tabs = response.json()
                    for tab in tabs[:3]:  # Show first 3 tabs
                        print(f"   - {tab.get('title', 'Unknown')} ({tab.get('url', 'Unknown URL')})")
                    return True
            except requests.RequestException:
                continue
        
        print("❌ Chrome started but remote debugging is not accessible")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start Chrome with debugging: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Chrome Remote Debugging Starter")
    print("=" * 40)
    
    if start_chrome_with_debugging():
        print("\n✨ Success! Chrome is ready for Selenium connection.")
        print("\nNext steps:")
        print("1. Navigate to https://quora.com in the Chrome window")
        print("2. Log in to your account")
        print("3. Run your scraper script")
        print("\nPress Ctrl+C to stop this script (Chrome will keep running)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Script stopped. Chrome will continue running with debugging enabled.")
    else:
        print("\n❌ Failed to start Chrome with debugging.")
        sys.exit(1) 