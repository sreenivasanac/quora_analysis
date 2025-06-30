# Scrapy settings for quora_scraper project

BOT_NAME = 'quora_scraper'

SPIDER_MODULES = ['quora_scraper.spiders']
NEWSPIDER_MODULE = 'quora_scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure delays for requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5
DOWNLOAD_DELAY = 0.3
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.3
AUTOTHROTTLE_MAX_DELAY = 1
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = True

# Configure concurrent requests
CONCURRENT_REQUESTS = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Configure user agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Configure pipelines
ITEM_PIPELINES = {
    'quora_scraper.pipelines.PostgreSQLPipeline': 300,
}

# Configure extensions
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'quora_scraper.middlewares.AuthMiddleware': 543,
}

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Cookie settings
COOKIES_ENABLED = True
COOKIES_DEBUG = True

# Request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'quora_scraper.log'

# Disable verbose third-party logging from selenium and urllib3
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'selenium.webdriver.remote.remote_connection': {
            'level': 'WARNING',
        },
        'urllib3.connectionpool': {
            'level': 'WARNING',
        },
    },
}

# Database settings (will be loaded from environment)
DATABASE_URL = None  # Set via environment variable 