#!/usr/bin/env python3
"""
Helper script to start multiple Chrome instances for parallel processing
"""

import os
import sys
import time
import platform
import subprocess
import argparse
import requests
import signal


def check_chrome_running(port):
    """Check if Chrome is running on a specific port"""
    try:
        response = requests.get(f'http://localhost:{port}/json', timeout=1)
        return response.status_code == 200
    except:
        return False


def start_chrome_instance(port, new_window=True):
    """Start a Chrome instance with remote debugging on specified port"""
    is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'

    if is_mac_arm:
        chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    else:
        chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        if not os.path.exists(chrome_path):
            # Try common Chrome paths for Linux/Windows
            possible_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium-browser',
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break

    if not os.path.exists(chrome_path) and platform.system() != 'Windows':
        print(f"ERROR: Chrome not found at {chrome_path}")
        print("Please install Google Chrome or update the path in this script.")
        return None

    # Build Chrome command
    chrome_cmd = [
        chrome_path,
        f'--remote-debugging-port={port}',
        f'--user-data-dir=/tmp/chrome_debug_profile_{port}'
    ]

    # Add new window flag if requested
    if new_window:
        chrome_cmd.append('--new-window')

    chrome_cmd.extend([
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-default-apps'
    ])

    print(f"Starting Chrome on port {port}...")

    # Start Chrome process
    try:
        if platform.system() == 'Darwin':  # macOS
            # For macOS, use 'open' command to properly launch Chrome
            process = subprocess.Popen(chrome_cmd,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        else:
            process = subprocess.Popen(chrome_cmd,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        return process
    except Exception as e:
        print(f"Failed to start Chrome on port {port}: {e}")
        return None


def stop_all_chrome_instances(base_port=9223, num_instances=5):
    """Stop all Chrome instances by closing their debug connections"""
    print("\nStopping Chrome instances...")
    stopped = 0

    for i in range(num_instances):
        port = base_port + i
        if check_chrome_running(port):
            try:
                # Try to close Chrome via CDP
                response = requests.get(f'http://localhost:{port}/json/close', timeout=1)
                if response.status_code == 200:
                    print(f"  Stopped Chrome on port {port}")
                    stopped += 1
            except:
                pass

    if stopped > 0:
        print(f"Stopped {stopped} Chrome instance(s)")
    else:
        print("No Chrome instances were running")


def main():
    parser = argparse.ArgumentParser(
        description='Start multiple Chrome instances for parallel Quora processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_parallel_chrome.py           # Start 3 Chrome instances (default)
  python start_parallel_chrome.py -n 5      # Start 5 Chrome instances
  python start_parallel_chrome.py --stop    # Stop all Chrome instances
  python start_parallel_chrome.py --check   # Check which ports have Chrome running
        """
    )

    parser.add_argument(
        '-n', '--num-instances',
        type=int,
        default=3,
        help='Number of Chrome instances to start (1-5, default: 3)'
    )

    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop all Chrome instances instead of starting them'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check which ports have Chrome running'
    )

    parser.add_argument(
        '--base-port',
        type=int,
        default=9223,
        help='Base port for Chrome debugging (default: 9223)'
    )

    args = parser.parse_args()

    # Validate number of instances
    if args.num_instances < 1 or args.num_instances > 5:
        print("ERROR: Number of instances must be between 1 and 5")
        sys.exit(1)

    # Handle stop command
    if args.stop:
        stop_all_chrome_instances(args.base_port, 5)
        sys.exit(0)

    # Handle check command
    if args.check:
        print("Checking Chrome instances...")
        running = []
        for i in range(5):
            port = args.base_port + i
            if check_chrome_running(port):
                running.append(port)
                print(f"  Port {port}: ✓ Chrome running")
            else:
                print(f"  Port {port}: ✗ Not running")

        if running:
            print(f"\nTotal: {len(running)} Chrome instance(s) running")
        else:
            print("\nNo Chrome instances are running")
        sys.exit(0)

    # Start Chrome instances
    print(f"Starting {args.num_instances} Chrome instance(s)...")
    print("=" * 60)

    processes = []
    started = 0
    skipped = 0

    for i in range(args.num_instances):
        port = args.base_port + i

        # Check if Chrome is already running on this port
        if check_chrome_running(port):
            print(f"Chrome already running on port {port} - skipping")
            skipped += 1
            continue

        # Start new Chrome instance
        process = start_chrome_instance(port, new_window=(i == 0))
        if process:
            processes.append(process)
            started += 1

            # Wait a bit for Chrome to start
            time.sleep(2)

            # Verify Chrome started
            if check_chrome_running(port):
                print(f"  ✓ Chrome started successfully on port {port}")
            else:
                print(f"  ✗ Chrome may have failed to start on port {port}")

    print("=" * 60)
    print(f"Summary: {started} started, {skipped} skipped")

    if started > 0:
        print("\nChrome instances are running. You can now:")
        print("1. Navigate to Quora.com in each window")
        print("2. Login if needed (use same account)")
        print("3. Run the parallel processor:")
        print(f"   python run_scraper.py --mode process --workers {args.num_instances}")
        print("\nPress Ctrl+C to stop all Chrome instances")

        # Wait for Ctrl+C
        try:
            signal.pause() if hasattr(signal, 'pause') else input("\nPress Enter to continue...")
        except KeyboardInterrupt:
            print("\n\nStopping Chrome instances...")
            stop_all_chrome_instances(args.base_port, args.num_instances)


if __name__ == "__main__":
    main()