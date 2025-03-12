import logging

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
            "filename": "logs_files/ai_bot_app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 3,
            "level": "DEBUG",
        },
    },
    "loggers": {
        "ai_bot_app": {
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
logger = logging.getLogger("ai_bot_app")
