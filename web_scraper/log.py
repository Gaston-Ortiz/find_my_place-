import logging
import logging.config
import logging.handlers
import os

# Logs live in <project root>/logs_files regardless of the current directory
# (/app/logs_files in the Docker image, where the cron job also writes).
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs_files"
)
os.makedirs(LOG_DIR, exist_ok=True)

# Define the logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Keeps existing loggers active
    "formatters": {
        "detailed": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(message)s"}
    },
    "handlers": {
        "custom_console": {  # Renamed console handler
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "level": "DEBUG",
        },
        "file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": os.path.join(LOG_DIR, "web_scraper.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 3,
            "level": "DEBUG",
        },
    },
    "loggers": {
        "web_scraper": {
            "handlers": ["custom_console", "file_handler"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
    "root": {
        "handlers": ["custom_console"],
        "level": "WARNING",
    },
}

# Apply the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("web_scraper")
