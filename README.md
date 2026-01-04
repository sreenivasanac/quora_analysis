# Quora Answer Scraper for Kanthaswamy Balasubramaniam

A comprehensive Scrapy-based web scraper to extract all 28,000+ answers from Quora user "Kanthaswamy Balasubramaniam" and store them in PostgreSQL.

## Features

- **Google OAuth Authentication**: Automated login via Google OAuth
- **Anti-Detection Technology**: Chrome DevTools Protocol (CDP) connection for stealth browsing
- **Centralized Chrome Management**: Singleton ChromeDriverManager eliminates code duplication
- **Respectful Scraping**: Configurable delays and concurrent request limits
- **PostgreSQL Storage**: Robust database storage with incremental saves and context managers
- **Enhanced Logging**: Separate file and console logging with single-line progress updates
- **Data Validation**: Critical field validation prevents saving incomplete data
- **Progress Monitoring**: Real-time logging and progress tracking
- **Error Handling**: Comprehensive retry logic and graceful error handling
- **Resume Capability**: Can resume from interruptions without data loss
- **Dual Mode Operation**: Separate collection and processing modes

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer (10-100x faster than pip)
- PostgreSQL database
- Google Chrome browser
- ChromeDriver (automatically managed)

## Installation

1. **Install uv** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Or via pip (if you have pip already)
   pip install uv
   ```

2. **Clone and setup the project:**
   ```bash
   cd quora_analysis
   uv pip install -e .
   ```
   
   > **Why uv?** uv is 10-100x faster than pip, has better dependency resolution, and provides a more reliable installation experience. All pip commands work with `uv pip`.

5. **Configure environment variables:**
   ```bash
   cp env_example.txt .env
   ```
   
   Edit `.env_example` with your database credentials:
   ```
   DATABASE_URL=
   GOOGLE_EMAIL=
   ```

## Usage

### Quick Start

1. **Test your setup:**
   ```bash
   python test_database_integration.py
   ```

2. **Run the interactive interface:**
   ```bash
   python main.py
   ```

### Manual Setup

1. **Initialize the database:**
   ```bash
   python setup_database.py
   ```

2. **Install processing dependencies** (if needed):
   ```bash
   uv pip install html-to-markdown pytz
   ```

3. **Run the scraper:**
   
   **Collection Mode** (collect answer URLs):
   ```bash
   python run_scraper.py --mode collect
   ```
   
   **Processing Mode** (populate answer data):
   ```bash
   python run_scraper.py --mode process
   ```

### Command Line Options

```bash
python run_scraper.py --help
```

**Available Modes:**
- `--mode collect` (default): Collect answer URLs from profile page
- `--mode process`: Process existing URLs and populate answer data

## How It Works

### Phase 1: Answer Link Discovery (Collection Mode)

1. **CDP Connection**: Connects to existing Chrome browser via Chrome DevTools Protocol
2. **Authentication**: Uses authenticated browser session for Google OAuth
3. **Infinite Scroll**: Scrolls through Kanthaswamy's answers page for 5 minutes to load all content
4. **Link Extraction**: Extracts answer URLs using CSS selector: `a.answer_timestamp::attr(href)`
5. **Duplicate Filtering**: Compares against existing database entries to avoid duplicates
6. **Database Storage**: Stores only new answer links in PostgreSQL with unique IDs
7. **Progress Tracking**: Logs progress in real-time during scrolling

### Phase 2: Answer Data Processing (Processing Mode)

1. **CDP Connection**: Reuses existing authenticated Chrome browser session
2. **Authentication Check**: Verifies Quora authentication before processing
3. **Database Query**: Retrieves incomplete entries (URLs without answer data)
4. **Answer Page Scraping**: Visits each answer URL using authenticated browser
5. **Data Extraction**: Extracts question text, answer content, revision links, timestamps
6. **HTML to Markdown**: Converts answer HTML content to clean Markdown format
7. **Timestamp Parsing**: Converts raw timestamps to timezone-aware datetime objects
8. **Database Updates**: Updates existing entries with complete answer data
9. **Progress Tracking**: Logs progress every 50 processed entries

### Database Schema

```sql
CREATE TABLE quora_answers (
    id SERIAL PRIMARY KEY,
    question_url TEXT,              -- URL of the question page
    answered_question_url TEXT,     -- URL of the specific answer (primary source)
    question_text TEXT,             -- The question title/text
    answer_content TEXT,            -- Answer content in Markdown format
    revision_link TEXT,             -- Link to answer revision history
    post_timestamp_raw TEXT,        -- Raw timestamp string from Quora
    post_timestamp_parsed TIMESTAMP WITH TIME ZONE -- Parsed timestamp with timezone (IST)
);
```

### Data Extraction Details

**Collection Mode** populates:
- `answered_question_url` - The primary answer URLs

**Processing Mode** populates:
- `question_url` - Extracted using CSS selector: `a.puppeteer_test_link:has(.puppeteer_test_question_title)`
- `question_text` - Extracted using CSS selector: `.puppeteer_test_question_title span`
- `answer_content` - Extracted from `div.q-text[style*='max-width: 100%'] span.q-box.qu-userSelect--text`, converted to Markdown
- `revision_link` - From `/log` page using selector: `a.puppeteer_test_link[href*='/log/revision/']`
- `post_timestamp_raw` - From `/log` page using selector: `span.c1h7helg.c8970ew:last-child`
- `post_timestamp_parsed` - Parsed from raw timestamp with Indian Standard Time (IST) timezone

**Note**: If critical fields (question_text and answer_content) fail to extract, the entire entry is skipped to prevent database corruption with empty values.

## Anti-Detection Technology

This scraper uses advanced techniques to avoid detection by Quora's anti-bot systems:

### Chrome DevTools Protocol (CDP) Connection

- **Stealth Browsing**: Connects to existing Chrome browser instead of launching new automated instances
- **Session Reuse**: Leverages existing authenticated sessions to avoid repeated logins
- **Natural Behavior**: Uses the same browser that a human would use for normal browsing

### Implementation Details

1. **CDP Setup**: Connects to Chrome running with `--remote-debugging-port=9222`
2. **WebDriver Masking**: Removes `navigator.webdriver` property to hide automation
3. **Minimal Chrome Options**: Uses only essential Chrome flags for maximum compatibility
4. **Authentication Reuse**: Shares authentication cookies between collection and processing modes
5. **Singleton ChromeDriverManager**: Centralizes all Chrome operations, eliminating code duplication
6. **Smart Connection**: Attempts to connect to existing Chrome instance before starting new one

### Browser Setup

Start Chrome with debugging enabled:
```bash
python start_chrome_debug.py
```

Or manually:
```bash
# macOS ARM (M1/M2/M3)
exec arch -arm64 /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug_profile

# macOS Intel
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_debug_profile

# Windows  
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome_debug_profile
```

### Testing Anti-Detection

Test your setup:
```bash
python test_answer_processor.py
```

This will verify:
- CDP connection to existing Chrome
- Authentication status
- Ability to access Quora pages without detection

## Configuration

### Scrapy Settings

Key settings in `quora_scraper/settings.py`:

- `DOWNLOAD_DELAY = 0.3` - Respectful delay between requests
- `CONCURRENT_REQUESTS = 3` - Maximum concurrent requests
- `AUTOTHROTTLE_ENABLED = True` - Automatic throttling based on response times

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GOOGLE_EMAIL` | Email for Google OAuth | Yes |
| `SCRAPY_LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | No |
| `SCRAPY_DOWNLOAD_DELAY` | Custom download delay | No |

## Performance Expectations

- **Runtime**: 8-10 hours for complete scraping
- **Target**: 28,000+ answers
- **Rate**: ~0.8-1.2 answers per second (respectful to Quora's servers)
- **Concurrency**: 1-3 concurrent requests

## Monitoring and Logging

### Log Files

- `quora_scraper.log` - Collection mode logs (URL gathering)
- `quora_process.log` - Processing mode logs (answer data extraction)
- `logs/processed_urls_YYYYMMDD_HHMMSS.log` - Detailed URL processing logs with timestamps
- Console output with clean single-line progress updates

### Logging Behavior

- **Console**: Shows minimal single-line progress updates (e.g., `Processing: 4/259 (1.5%) | Success: 4 | Failed: 0`)
- **File Logs**: Contains detailed processing information, URLs, and error messages
- **Failed URLs**: Displayed in console for immediate visibility

### Progress Tracking

```
INFO - Progress: 100 new answers processed. Total in DB: 100
INFO - Progress: 200 new answers processed. Total in DB: 200
INFO - Page 5: Found 23 answer links. Total so far: 487
```

### Database Status

Check current status:
```bash
python -c "
from quora_scraper.database_sqlite import DatabaseManager
import os
from dotenv import load_dotenv
load_dotenv()
db = DatabaseManager()
db.connect()
print(f'Total answers: {db.get_answer_count()}')
db.disconnect()
"
```

## Error Handling

### Common Issues

1. **Authentication Failure**:
   - Ensure Chrome is installed
   - Check Google account credentials
   - Complete manual authentication when prompted

2. **Database Connection Issues**:
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database exists and user has permissions

3. **Rate Limiting**:
   - Scraper automatically handles rate limits
   - Increase DOWNLOAD_DELAY if needed

### Graceful Shutdown

- Press `Ctrl+C` to stop scraping
- Data is saved incrementally, so no loss on interruption
- Resume by running the scraper again

## Project Structure

```
quora_analysis/
├── quora_scraper/
│   ├── __init__.py
│   ├── settings.py              # Scrapy configuration
│   ├── items.py                 # Data item definitions
│   ├── pipelines.py             # Data processing pipelines
│   ├── middlewares.py           # Authentication middleware
│   ├── database.py              # Database management with context managers
│   ├── chrome_driver_manager.py # Centralized Chrome driver management
│   ├── answer_processor.py      # Answer data extraction and processing
│   ├── common.py                # Common utilities and authentication checks
│   └── spiders/
│       ├── __init__.py
│       └── quora_profile_spider.py  # Main spider
├── main.py                      # Interactive interface
├── run_scraper.py              # Direct scraper runner
├── setup_database.py           # Database initialization
├── test_database_integration.py  # Database testing
├── test_answer_processor.py    # Answer processor testing
├── scrapy.cfg                  # Scrapy project config
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore file
├── CLAUDE.md                   # Claude AI guidance file
├── pyproject.toml              # Project dependencies
└── README.md                   # This file
```

## Implementation Status

This implementation covers both phases from the requirements:

### ✅ Phase 1: Answer Link Discovery (Collection Mode)
- Answer URL collection from profile page
- Database storage with unique IDs
- Duplicate detection and filtering
- Progress tracking and logging

### ✅ Phase 2: Answer Data Processing (Processing Mode)
- Individual answer page scraping
- Question text extraction
- Answer content conversion to Markdown using `html-to-markdown`
- Revision log data collection
- Timestamp parsing with timezone support
- Database updates with complete answer data
- Error handling and retry logic

### Usage Workflow

1. **First Run**: Use collection mode to gather all answer URLs
   ```bash
   python run_scraper.py --mode collect
   ```

2. **Second Run**: Use processing mode to populate answer data
   ```bash
   python run_scraper.py --mode process
   ```

3. **Monitor Progress**: Check database status anytime
   ```bash
   python main.py  # Option 4: Check status
   ```

## Contributing

1. Follow the existing code style
2. Add appropriate logging
3. Include error handling
4. Test with small datasets first

## License

This project is for educational and research purposes only. Please respect Quora's terms of service and rate limits.
