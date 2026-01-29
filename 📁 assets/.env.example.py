# ==============================================
# FOOTBALL DATA SCRAPER PRO - CONFIGURATION FILE
# ==============================================

# API CONFIGURATION
# --------------------------------------------------
# Get your free API key from: https://www.football-data.org/
# Free tier limits: 10 requests per minute, 500 per month
FOOTBALL_DATA_API_KEY=your_api_key_here

# DATABASE CONFIGURATION
# --------------------------------------------------
# SQLite database path (relative or absolute)
DB_PATH=football_data.db
# DB_PATH=/path/to/custom/location/football_data.db

# APPLICATION SETTINGS
# --------------------------------------------------
# Default championship for startup
DEFAULT_CHAMPIONSHIP=Premier League

# Date range for initial data loading
INITIAL_DAYS_BACK=30

# Cache settings (in seconds)
CACHE_DURATION_DYNAMIC=300    # 5 minutes for live data
CACHE_DURATION_STATIC=3600    # 1 hour for static data

# API RATE LIMITING
# --------------------------------------------------
# Maximum requests per minute (respect API limits)
MAX_REQUESTS_PER_MINUTE=8     # Keep below 10 for free tier

# Request timeout in seconds
REQUEST_TIMEOUT=30
REQUEST_RETRY_COUNT=3

# USER INTERFACE SETTINGS
# --------------------------------------------------
# Streamlit specific settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
STREAMLIT_THEME=light

# Tkinter specific settings
TKINTER_WINDOW_WIDTH=1600
TKINTER_WINDOW_HEIGHT=900
TKINTER_REFRESH_INTERVAL=30000  # 30 seconds

# DATA RETENTION
# --------------------------------------------------
# Days to keep match data (0 = keep forever)
DATA_RETENTION_DAYS=365

# Auto-delete old data (true/false)
AUTO_CLEANUP=true
CLEANUP_SCHEDULE_HOUR=3        # 3 AM daily

# LOGGING CONFIGURATION
# --------------------------------------------------
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file location
LOG_FILE=football_scraper.log
# LOG_FILE=/var/log/football_scraper.log

# Maximum log file size in MB
MAX_LOG_SIZE=10
LOG_BACKUP_COUNT=3

# EXPORT SETTINGS
# --------------------------------------------------
# Default export format (csv, excel, json)
DEFAULT_EXPORT_FORMAT=csv

# Default export location
EXPORT_DEFAULT_PATH=./exports

# NOTIFICATION SETTINGS (Future feature)
# --------------------------------------------------
# Email notifications for scraping errors
NOTIFY_ON_ERROR=false
NOTIFICATION_EMAIL=your_email@example.com

# SMTP configuration for email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# ADVANCED SETTINGS
# --------------------------------------------------
# Proxy settings (if behind corporate firewall)
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=https://proxy.example.com:8080
# NO_PROXY=localhost,127.0.0.1

# SSL verification (set to false for self-signed certs)
VERIFY_SSL=true

# Database connection pool size
DB_POOL_SIZE=5

# Memory cache size (in MB)
MAX_CACHE_SIZE=50

# DEBUG SETTINGS
# --------------------------------------------------
# Enable debug mode (shows more information)
DEBUG_MODE=false

# Mock API responses for testing (true/false)
MOCK_API=false

# Test database path
TEST_DB_PATH=test_football_data.db

# ==============================================
# DO NOT COMMIT ACTUAL API KEYS TO VERSION CONTROL
# ==============================================
# This is a template file. Copy to .env and fill in your values.
# Add .env to .gitignore to prevent accidental commits.