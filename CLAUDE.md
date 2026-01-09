# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Quora Answer Scraper designed to extract all answers from a specific Quora user profile (e.g., Kanthaswamy Balasubramaniam) and store them in SQLite db. The project uses Scrapy with Chrome DevTools Protocol (CDP) for stealth browsing and anti-detection, plus a React/Flask visualization dashboard.

## Key Commands

### Setup and Installation
```bash
# Install dependencies (requires uv - faster than pip)
uv pip install -e .

# Initialize database
python scripts/setup_database.py

# Interactive interface
python scripts/main.py
```

### Running the Scraper
```bash
# Collection mode: Collect answer URLs from profile page
python scripts/run_scraper.py --mode collect

# Sequential processing mode: Process URLs one at a time
python scripts/run_scraper.py --mode process

# Parallel processing mode: Process URLs with multiple workers
python scripts/run_scraper.py --mode process --workers 3  # 3 parallel workers
python scripts/run_scraper.py --mode process --workers 5  # 5 parallel workers (max)

# Start Chrome instances for parallel processing
python scripts/start_parallel_chrome.py -n 3  # Start 3 Chrome instances
python scripts/start_parallel_chrome.py --check  # Check running instances
python scripts/start_parallel_chrome.py --stop  # Stop all instances
```

### Testing
```bash
# Test database connectivity
python tests/test_database_integration.py

# Test Chrome CDP connection and authentication
python tests/test_answer_processor.py

# Test timestamp parsing
python tests/test_timestamp_parsing.py

# Test parallel processing setup
python tests/test_parallel_setup.py
```

### Visualization Dashboard
```bash
# Start backend server
cd visualization && python visualization_backend.py

# Start frontend development server
cd visualization/visualization_frontend && npm start

# Build for production
cd visualization/visualization_frontend && npm run build
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
- **DatabaseManager**: Handles all SQLite operations
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
  - Each worker uses separate Chrome instance (ports 9223-9227 for process mode)
  - Collection mode uses port 9222 (default)
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

### Visualization System (NEW)

#### Backend (`visualization/visualization_backend.py`)
- Flask API server with CORS support
- Endpoints:
  - `/api/timestamps`: Get timestamps for date range with timezone conversion
  - `/api/timestamps/all`: Get all timestamps for calendar view
  - `/api/stats`: Get posting statistics
  - `/api/health`: Health check endpoint
- Uses shared utilities from `utils/` directory

#### Frontend (`visualization/visualization_frontend/`)
- React-based dashboard built with Create React App
- Components:
  - Calendar heatmap view showing answer frequency
  - Weekly posting patterns analysis
  - Timezone-aware data visualization (IST, CST, PST, EST)
  - Question popovers on hover
- Production build served via Vercel

#### Deployment (Vercel)
- Configuration in `vercel.json`
- API serverless functions in `api/` directory
- Static frontend build from `visualization/visualization_frontend/build`
- Shared utilities in `utils/` for database and timezone operations

## Important Notes

- **Chrome Debugging**:
  - Collection mode: Chrome on port 9222 (default)
  - Process mode: Chrome on ports 9223+ (9223, 9224, 9225...)
  - Allows running both modes simultaneously
- **Authentication**: Uses existing Google OAuth session in browser
- **Database**: SQLite required with specific schema
- **Rate Limiting**: Respectful scraping with 0.3s delays between requests
- **Logging**:
  - Collection mode: `quora_scraper.log`
  - Processing mode: `quora_process.log`
  - URL processing: `logs/processed_urls_YYYYMMDD_HHMMSS.log`
  - Console shows clean single-line progress updates

## File Structure

- `scripts/main.py` - Interactive CLI interface
- `scripts/run_scraper.py` - Direct scraper runner with mode selection (supports --workers)
- `scripts/setup_database.py` - Database initialization
- `scripts/start_parallel_chrome.py` - Helper to start multiple Chrome instances (NEW)
- `tests/test_*.py` - Various test scripts for different components
- `quora_scraper/` - Main Scrapy project directory
  - `chrome_driver_manager.py` - Centralized Chrome driver management (singleton)
  - `spiders/quora_profile_spider.py` - Core spider implementation
  - `database.py` - Database operations with context managers
  - `answer_processor.py` - Sequential answer data extraction with enhanced logging
  - `parallel_answer_processor.py` - Parallel processing with multiple workers (NEW)
  - `middlewares.py` - Chrome CDP and authentication (uses ChromeDriverManager)
  - `common.py` - Shared utilities and authentication checking
  - `settings.py` - Scrapy configuration
- `visualization/` - Data visualization components (NEW)
  - `visualization_backend.py` - Flask API server
  - `visualization_frontend/` - React dashboard
- `api/` - Vercel serverless functions
- `utils/` - Shared utilities for database and timezone operations
- `vercel.json` - Vercel deployment configuration

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
- For visualization changes, test locally with both backend and frontend running

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

### Visualization Dashboard (NEW)
- Added interactive data visualization for collected answers
- Timezone-aware analysis of posting patterns
- Calendar heatmap for answer frequency over time
- Deployed to Vercel with serverless API functions
