from django.contrib.messages import constants as messages
from coldfront.core.utils.common import import_from_settings
import socket

# ------------------------------------------------------------------------------
# ColdFront logging config
# ------------------------------------------------------------------------------

LOG_FILE_BASE = import_from_settings("COLDFRONT_DJANGO_LOG_FILE")
try:
    HOSTNAME = socket.gethostname()
except Exception:
    HOSTNAME = "-"
LOG_FILE = f"{LOG_FILE_BASE}.{HOSTNAME}"

MESSAGE_TAGS = {
    messages.DEBUG: "info",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["file"]},
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {module} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": LOG_FILE,
            "maxBytes": 1024 * 1024,
            "backupCount": 3,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}
