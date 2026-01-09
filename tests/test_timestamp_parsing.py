#!/usr/bin/env python3
"""
Test script to verify timestamp parsing functionality
"""

import sys
import os
from datetime import datetime
import pytz

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def parse_quora_timestamp(timestamp_str: str):
    """Convert Quora timestamp string to datetime object with timezone"""
    if not timestamp_str:
        return None
        
    try:
        # Parse the timestamp string (e.g., "June 27, 2025 at 10:26:56 PM")
        dt = datetime.strptime(timestamp_str, "%B %d, %Y at %I:%M:%S %p")
        
        # Set timezone to Indian Standard Time (IST)
        ist = pytz.timezone('Asia/Kolkata')
        dt_with_tz = ist.localize(dt)
        
        return dt_with_tz
    except ValueError as e:
        print(f"Error parsing timestamp: {timestamp_str} - {e}")
        return None

def test_timestamp_parsing():
    """Test the timestamp parsing function"""
    test_cases = [
        "June 24, 2025 at 8:30:01 AM",
        "June 27, 2025 at 10:26:56 PM",
        "December 31, 2024 at 11:59:59 PM",
        "January 1, 2025 at 12:00:00 AM"
    ]
    
    print("Testing timestamp parsing:")
    print("=" * 50)
    
    for timestamp_str in test_cases:
        parsed = parse_quora_timestamp(timestamp_str)
        print(f"Input:  {timestamp_str}")
        print(f"Output: {parsed}")
        print(f"ISO:    {parsed.isoformat() if parsed else 'None'}")
        print("-" * 30)

if __name__ == "__main__":
    test_timestamp_parsing() 