# Implementation Notes (Detailed)

This document contains the detailed implementation and operational notes that used to live in the root `README.md`.

## How It Works

### Phase 1: Answer Link Discovery (Collection Mode)

1. **CDP Connection**: Connects to existing Chrome browser via Chrome DevTools Protocol
2. **Authentication**: Uses authenticated browser session for Google OAuth
3. **Infinite Scroll**: Scrolls through the target user's answers page to load content
4. **Link Extraction**: Extracts answer URLs
5. **Duplicate Filtering**: Compares against existing database entries to avoid duplicates
6. **Database Storage**: Stores only new answer links
7. **Progress Tracking**: Logs progress in real-time during scrolling

### Phase 2: Answer Data Processing (Processing Mode)

1. **CDP Connection**: Reuses existing authenticated Chrome browser session
2. **Authentication Check**: Verifies Quora authentication before processing
3. **Database Query**: Retrieves incomplete entries (URLs without answer data)
4. **Answer Page Scraping**: Visits each answer URL using authenticated browser
5. **Data Extraction**: Extracts question text, answer content, revision links, timestamps
6. **HTML to Markdown**: Converts answer HTML content to Markdown
7. **Timestamp Parsing**: Converts raw timestamps to timezone-aware datetime objects
8. **Database Updates**: Updates existing entries with complete answer data
9. **Progress Tracking**: Logs periodic progress

## Database Schema

```sql
CREATE TABLE quora_answers (
    id SERIAL PRIMARY KEY,
    question_url TEXT,              -- URL of the question page
    answered_question_url TEXT,     -- URL of the specific answer (primary source)
    question_text TEXT,             -- The question title/text
    answer_content TEXT,            -- Answer content in Markdown format
    revision_link TEXT,             -- Link to answer revision history
    post_timestamp_raw TEXT,        -- Raw timestamp string from Quora
    post_timestamp_parsed TIMESTAMP WITH TIME ZONE -- Parsed timestamp with timezone
);
```

## Data Extraction Details

**Collection Mode** populates:
- `answered_question_url` - The primary answer URLs

**Processing Mode** populates:
- `question_url`
- `question_text`
- `answer_content` (converted to Markdown)
- `revision_link`
- `post_timestamp_raw`
- `post_timestamp_parsed`

## Anti-Detection Technology

This scraper relies on connecting to an existing, user-authenticated Chrome instance via CDP to reduce bot detection and reuse sessions.

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
"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" \
  --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome_debug_profile
```

### Testing CDP/Auth

```bash
python tests/test_answer_processor.py
```

## Configuration

### Scrapy Settings

Key settings in `quora_scraper/settings.py`:

- `DOWNLOAD_DELAY = 0.3`
- `CONCURRENT_REQUESTS = 3`
- `AUTOTHROTTLE_ENABLED = True`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | Yes |
| `GOOGLE_EMAIL` | Email for Google OAuth | Yes |
| `SCRAPY_LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | No |
| `SCRAPY_DOWNLOAD_DELAY` | Custom download delay | No |

## Monitoring and Logging

### Log Files

- `quora_scraper.log` - Collection mode logs (URL gathering)
- `quora_process.log` - Processing mode logs (answer data extraction)
- `logs/processed_urls_YYYYMMDD_HHMMSS.log` - Detailed per-run URL processing log

### Database Status

```bash
python -c "
from quora_scraper.database_sqlite import DatabaseManager
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

1. **Authentication Failure**: ensure Chrome is running with remote debugging and that you are logged into Quora.
2. **Database Connection Issues**: verify `DATABASE_URL` and DB availability.
3. **Rate Limiting**: increase delay/concurrency limits as needed.

### Graceful Shutdown

- Press `Ctrl+C` to stop scraping.
- Data is saved incrementally; you can resume by rerunning.

## Project Structure

```
quora_analysis/
├── quora_scraper/
├── scripts/
├── tests/
├── visualization/
└── README.md
```

## Implementation Status

The project supports two phases:

- **Collection Mode**: collects answer URLs from the profile page
- **Processing Mode**: visits collected URLs and extracts complete answer data
