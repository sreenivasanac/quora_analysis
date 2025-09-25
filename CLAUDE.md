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

# Processing mode: Process existing URLs and populate answer data
python run_scraper.py --mode process
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

#### Database Layer (`quora_scraper/database.py`)
- **DatabaseManager**: Handles all PostgreSQL operations
- Schema: `quora_answers` table with fields for URLs, question text, answer content, timestamps
- Incremental processing: tracks complete vs incomplete entries

#### Scrapy Framework
- **Spider**: `quora_scraper/spiders/quora_profile_spider.py` - main scraper logic
- **Middleware**: `quora_scraper/middlewares.py` - Chrome CDP connection and authentication
- **Pipelines**: `quora_scraper/pipelines.py` - data processing and database storage
- **Settings**: `quora_scraper/settings.py` - rate limiting, delays, user agents

#### Anti-Detection System
- **Chrome CDP Connection**: Connects to existing Chrome browser instance instead of launching automated browser
- **Session Reuse**: Leverages existing authenticated sessions
- **Rate Limiting**: Configurable delays (0.3s default) and concurrent request limits (3 max)

#### Answer Processing (`quora_scraper/answer_processor.py`)
- Extracts question text, answer content, revision links, timestamps
- Converts HTML to Markdown using `html2text`
- Parses timestamps with timezone support (IST)

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
- **Logging**: Separate log files for collection (`quora_scraper.log`) and processing (`quora_process.log`)

## File Structure

- `main.py` - Interactive CLI interface
- `run_scraper.py` - Direct scraper runner with mode selection
- `setup_database.py` - Database initialization
- `quora_scraper/` - Main Scrapy project directory
  - `spiders/quora_profile_spider.py` - Core spider implementation
  - `database.py` - Database operations
  - `answer_processor.py` - Answer data extraction
  - `middlewares.py` - Chrome CDP and authentication
  - `settings.py` - Scrapy configuration

## Development Tips

- Always test database connection first with `test_database_integration.py`
- Use Chrome debugging mode for development: `python start_chrome_debug.py`
- Monitor progress through log files and console output
- Database operations are incremental - can resume after interruption
- Check authentication status before processing with `test_answer_processor.py`