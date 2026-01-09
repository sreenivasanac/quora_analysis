#!/usr/bin/env python3
"""
Test script to verify parallel processing setup
"""

import sys
import time
import requests
from quora_scraper.parallel_answer_processor import ParallelChromeManager


def test_chrome_ports(num_workers=3):
    """Test if Chrome instances can be reached on required ports"""
    print(f"Testing Chrome setup for {num_workers} workers...")
    print("=" * 60)

    base_port = 9223
    available_ports = []
    missing_ports = []

    # Test ports from 9223 to 9223+num_workers-1
    for i in range(num_workers):
        port = base_port + i
        try:
            response = requests.get(f'http://localhost:{port}/json', timeout=2)
            if response.status_code == 200:
                print(f"✓ Port {port}: Chrome is running")
                available_ports.append(port)
            else:
                print(f"✗ Port {port}: Chrome not responding properly")
                missing_ports.append(port)
        except Exception:
            print(f"✗ Port {port}: Chrome not running")
            missing_ports.append(port)

    print("=" * 60)

    if missing_ports:
        print(f"\n⚠️  Missing Chrome instances on ports: {missing_ports}")
        print("\nTo start Chrome instances, run:")
        print(f"  python scripts/start_parallel_chrome.py -n {num_workers}")
        return False
    else:
        print(f"\n✅ All {num_workers} Chrome instances are running!")
        return True


def test_chrome_connection(port):
    """Test if we can connect to a Chrome instance"""
    print(f"\nTesting connection to Chrome on port {port}...")

    try:
        manager = ParallelChromeManager(debug_port=port)

        if manager.connect_to_existing_chrome():
            print(f"✓ Successfully connected to Chrome on port {port}")

            # Check authentication
            manager.driver.get("https://www.quora.com")
            time.sleep(2)

            if manager.check_authentication():
                print(f"✓ Authenticated to Quora on port {port}")
            else:
                print(f"⚠️  Not authenticated to Quora on port {port}")
                print("  Please login manually in the Chrome window")

            manager.cleanup()
            return True
        else:
            print(f"✗ Failed to connect to Chrome on port {port}")
            return False
    except Exception as e:
        print(f"✗ Error connecting to Chrome on port {port}: {e}")
        return False


def main():
    print("Parallel Processing Setup Test")
    print("=" * 60)

    # Test different worker configurations
    test_configs = [1, 3, 5]

    for num_workers in test_configs:
        print(f"\n📍 Testing {num_workers} worker(s) configuration:")
        if test_chrome_ports(num_workers):
            # Test connection to first port
            test_chrome_connection(9223)
            break
        else:
            response = input(f"\nStart {num_workers} Chrome instances now? (y/N): ")
            if response.lower() == 'y':
                import os
                import subprocess

                repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                subprocess.run([sys.executable, os.path.join(repo_root, "scripts", "start_parallel_chrome.py"), "-n", str(num_workers)])
                time.sleep(5)  # Wait for Chrome to start
                if test_chrome_ports(num_workers):
                    test_chrome_connection(9223)
                    break

    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    main()