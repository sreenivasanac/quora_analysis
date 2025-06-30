#!/usr/bin/env python3
"""
Quora Answer Scraper for Kanthaswamy Balasubramaniam
Main entry point for the scraper application
"""

import os
import sys
import subprocess

def main():
    """Main entry point for the Quora scraper"""
    print("=" * 70)
    print("Quora Answer Scraper for a particular profile (e.g. Kanthaswamy Balasubramaniam)")
    print("=" * 70)
    print()
    
    print("Available commands:")
    print("1. Setup database - Initialize PostgreSQL tables")
    print("2. Collect URLs - Scrape and collect answer URLs from profile page")
    print("3. Process answers - Process existing URLs and populate answer data")
    print("4. Check status - View current database status")
    print("5. Exit")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                print("\nRunning database setup...")
                subprocess.run([sys.executable, "setup_database.py"])
                print()
                
            elif choice == "2":
                print("\nStarting URL collection...")
                print("This will collect answer URLs from Quora profile page. (e.g. Kanthaswamy Balasubramaniam)")
                print("Note: This will open a browser window for authentication.")
                print("Make sure you have Chrome installed and your .env file configured.")
                print("Log file: quora_scraper.log")
                print()
                confirm = input("Continue? (y/N): ")
                if confirm.lower() == 'y':
                    subprocess.run([sys.executable, "run_scraper.py", "--mode", "collect"])
                print()
                
            elif choice == "3":
                print("\nStarting answer processing...")
                print("This will process existing answer URLs and populate:")
                print("- Question URLs and text")
                print("- Answer content (converted to Markdown)")
                print("- Revision links and timestamps")
                print("Log file: quora_process.log")
                print()
                print("REQUIREMENTS:")
                print("- Existing answer URLs in database")
                print("- Processing takes 2-3 seconds per answer")
                print()
                confirm = input("Continue? (y/N): ")
                if confirm.lower() == 'y':
                    subprocess.run([sys.executable, "run_scraper.py", "--mode", "process"])
                print()
                
            elif choice == "4":
                print("\nChecking database status...")
                subprocess.run([sys.executable, "-c", """
                import os
                from dotenv import load_dotenv
                from quora_scraper.database import DatabaseManager

                load_dotenv()
                try:
                    db = DatabaseManager()
                    db.connect()
                    total_count = db.get_answer_count()
                    incomplete_count = db.get_incomplete_count()
                    complete_count = total_count - incomplete_count
                    
                    print(f'Total answers in database: {total_count}')
                    print(f'Complete entries (with answer data): {complete_count}')
                    print(f'Incomplete entries (URLs only): {incomplete_count}')
                    
                    if incomplete_count > 0:
                        print(f'\\nYou can process {incomplete_count} incomplete entries using:')
                        print('python run_scraper.py --mode process')
                    
                    db.disconnect()
                except Exception as e:
                    print(f'Error: {e}')
                                """])
                print()
                
            elif choice == "5":
                print("Goodbye!")
                break
                
            else:
                print("Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
