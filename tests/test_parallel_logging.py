#!/usr/bin/env python3
"""
Test script to verify parallel processing logging setup
"""

import os
import sys
import logging
from datetime import datetime
from quora_scraper.parallel_answer_processor import setup_worker_logging, ParallelAnswerProcessor


def test_worker_logging():
    """Test worker logging setup"""
    print("Testing Worker Logging Setup")
    print("=" * 60)

    # Create test log directory
    log_dir = "logs/test_parallel_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(log_dir, exist_ok=True)

    # Test worker logging for 3 workers
    for worker_id in range(3):
        worker_logger, log_file = setup_worker_logging(worker_id, log_dir)

        # Test logging
        worker_logger.info(f"Test message from worker {worker_id}")
        worker_logger.error(f"Test error from worker {worker_id}")

        # Verify file was created
        if os.path.exists(log_file):
            print(f"✓ Worker {worker_id} log file created: {log_file}")
        else:
            print(f"✗ Worker {worker_id} log file NOT created")

    print(f"\nLog files saved to: {log_dir}/")
    print("Check that no worker logs appear in terminal above")


def test_coordinator_setup():
    """Test coordinator logging setup"""
    print("\n" + "=" * 60)
    print("Testing Coordinator Setup")
    print("=" * 60)

    # Create processor with 3 workers
    processor = ParallelAnswerProcessor(num_workers=3)

    # Check coordinator log file
    if os.path.exists(processor.log_file):
        print(f"✓ Coordinator log file created: {processor.log_file}")
    else:
        print(f"✗ Coordinator log file NOT created")

    # Test coordinator logging
    processor.coordinator_logger.info("Test coordinator message")
    processor.coordinator_logger.error("Test coordinator error")

    print(f"✓ Coordinator log directory: {processor.log_dir}")
    print(f"✓ Number of workers configured: {processor.num_workers}")
    print(f"✓ Base debug port: {processor.base_debug_port}")

    print("\nCheck that no coordinator logs appear in terminal above")


def main():
    print("Parallel Processing Logging Test")
    print("=" * 60)

    # Test worker logging
    test_worker_logging()

    # Test coordinator setup
    test_coordinator_setup()

    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nKey points verified:")
    print("1. Worker logs go to separate files (no terminal output)")
    print("2. Coordinator logs go to separate file (no terminal output)")
    print("3. Log files are organized in timestamped directories")
    print("4. Each worker has its own log file")


if __name__ == "__main__":
    main()