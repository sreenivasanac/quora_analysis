# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Quora Answer Scraper designed to extract all answers from a specific Quora user profile (e.g., Kanthaswamy Balasubramaniam) and store them in PostgreSQL. The project uses Scrapy with Chrome DevTools Protocol (CDP) for stealth browsing and anti-detection.

## Key Commands

### Setup and Installation
```bash
# Install dependencies (requires uv - faster than pip)
uv pip install -e .

# Initialize database
python setup_database.py

# Interactive interface
python main.py
```

### Running the Scraper
```bash
# Collection mode: Collect answer URLs from profile page
python run_scraper.py --mode collect

# Sequential processing mode: Process URLs one at a time
python run_scraper.py --mode process

# Parallel processing mode: Process URLs with multiple workers
python run_scraper.py --mode process --workers 3  # 3 parallel workers
python run_scraper.py --mode process --workers 5  # 5 parallel workers (max)

# Start Chrome instances for parallel processing
python start_parallel_chrome.py -n 3  # Start 3 Chrome instances
python start_parallel_chrome.py --check  # Check running instances
python start_parallel_chrome.py --stop  # Stop all instances
```

### Testing
```bash
# Test database connectivity
python test_database_integration.py

# Test Chrome CDP connection and authentication
python test_answer_processor.py

# Test timestamp parsing
python test_timestamp_parsing.py
```

### Development Tools
```bash
# Code formatting (if available)
black .
flake8 .

# Start Chrome with debugging for manual testing
python start_chrome_debug.py
```

## Architecture Overview

### Two-Phase Operation
1. **Collection Mode**: Scrolls through Quora profile page to collect all answer URLs
2. **Processing Mode**: Visits individual answer pages to extract complete data (question text, answer content, timestamps)

### Core Components

#### Chrome Driver Management (`quora_scraper/chrome_driver_manager.py`)
- **ChromeDriverManager**: Centralized Chrome driver operations using singleton pattern
- **Key Features**:
  - Eliminates ~395+ lines of duplicate code across modules
  - Singleton pattern via `get_chrome_manager()`
  - Smart CDP connection - tries existing Chrome before starting new instance
  - Platform-specific driver setup (Mac ARM, Intel, Windows)
  - Stealth mode application to hide automation

#### Database Layer (`quora_scraper/database.py`)
- **DatabaseManager**: Handles all PostgreSQL operations
- **database_context()**: Context manager for safe database operations
- Schema: `quora_answers` table with fields for URLs, question text, answer content, timestamps
- Incremental processing: tracks complete vs incomplete entries
- Data validation: Prevents saving empty/None values for critical fields

#### Scrapy Framework
- **Spider**: `quora_scraper/spiders/quora_profile_spider.py` - main scraper logic
- **Middleware**: `quora_scraper/middlewares.py` - Chrome CDP connection and authentication
- **Pipelines**: `quora_scraper/pipelines.py` - data processing and database storage
- **Settings**: `quora_scraper/settings.py` - rate limiting, delays, user agents

#### Anti-Detection System
- **Chrome CDP Connection**: Connects to existing Chrome browser instance instead of launching automated browser
- **Session Reuse**: Leverages existing authenticated sessions
- **Rate Limiting**: Configurable delays (0.3s default) and concurrent request limits (3 max)

#### Answer Processing (`quora_scraper/answer_processor.py` and `parallel_answer_processor.py`)
- **QuoraAnswerProcessor**: Sequential processing of existing database entries
- **ParallelAnswerProcessor**: Parallel processing with multiple workers (NEW)
- **Key Features**:
  - Extracts question text, answer content, revision links, timestamps
  - Converts HTML to Markdown using `html2text`
  - Parses timestamps with timezone support (IST)
  - Critical field validation (question_text and answer_content required)
  - Enhanced logging system:
    - File logging to `logs/processed_urls_YYYYMMDD_HHMMSS.log`
    - Single-line progress updates in terminal
    - Separate URL logger that doesn't propagate to console
  - Failed URL tracking and reporting

##### Parallel Processing Architecture (NEW)
- **Multi-worker Processing**: 1-5 parallel workers (default: 3)
- **Chrome Instance Management**:
  - Each worker uses separate Chrome instance (ports 9222-9226)
  - Automatic Chrome startup if not running
  - Independent browser sessions per worker
- **Work Distribution**:
  - URLs evenly divided among workers
  - No duplicate processing
  - Each worker has own database connection
- **Progress Tracking**:
  - Real-time aggregated progress from all workers
  - ETA calculation based on processing rate
  - Failed URL collection across workers
- **Performance**: 3-5x faster than sequential processing

## Environment Configuration

Create `.env` file from `.env_example`:
```
DATABASE_URL=postgresql://username:password@localhost/quora_analysis
GOOGLE_EMAIL=your_email@example.com
```

## Important Notes

- **Chrome Debugging**: Scraper connects to Chrome running with `--remote-debugging-port=9222`
- **Authentication**: Uses existing Google OAuth session in browser
- **Database**: PostgreSQL required with specific schema
- **Rate Limiting**: Respectful scraping with 0.3s delays between requests
- **Logging**:
  - Collection mode: `quora_scraper.log`
  - Processing mode: `quora_process.log`
  - URL processing: `logs/processed_urls_YYYYMMDD_HHMMSS.log`
  - Console shows clean single-line progress updates

## File Structure

- `main.py` - Interactive CLI interface
- `run_scraper.py` - Direct scraper runner with mode selection (supports --workers)
- `setup_database.py` - Database initialization
- `start_parallel_chrome.py` - Helper to start multiple Chrome instances (NEW)
- `quora_scraper/` - Main Scrapy project directory
  - `chrome_driver_manager.py` - Centralized Chrome driver management (singleton)
  - `spiders/quora_profile_spider.py` - Core spider implementation
  - `database.py` - Database operations with context managers
  - `answer_processor.py` - Sequential answer data extraction with enhanced logging
  - `parallel_answer_processor.py` - Parallel processing with multiple workers (NEW)
  - `middlewares.py` - Chrome CDP and authentication (uses ChromeDriverManager)
  - `common.py` - Shared utilities and authentication checking
  - `settings.py` - Scrapy configuration

## Development Tips

- Always test database connection first with `test_database_integration.py`
- Use Chrome debugging mode for development: `python start_chrome_debug.py`
- Monitor progress through log files and console output
- Database operations are incremental - can resume after interruption
- Check authentication status before processing with `test_answer_processor.py`
- Chrome driver is managed centrally - use `get_chrome_manager()` to access
- Database operations should use `database_context()` context manager
- Critical fields (question_text, answer_content) are validated before saving
- Failed URLs are tracked and reported at the end of processing

## Recent Architecture Improvements

### Code Refactoring (Eliminated ~395+ lines of duplication)
- Created `ChromeDriverManager` class as central Chrome management
- Implemented singleton pattern for driver sharing
- Removed duplicate Chrome setup code from spider, middleware, and processor

### Enhanced Error Handling
- Critical field validation prevents database corruption
- Failed URLs are tracked and displayed
- Better separation of concerns between modules

### Improved Logging
- File and console logging are separated
- URL processing details go to timestamped log files
- Console shows clean, single-line progress updates
- Reduced verbose output (e.g., Chrome tab information)