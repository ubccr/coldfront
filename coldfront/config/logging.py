from django.contrib.messages import constants as messages
from coldfront.core.utils.common import import_from_settings

# ------------------------------------------------------------------------------
# ColdFront logging config
# ------------------------------------------------------------------------------

LOG_FILE = import_from_settings("COLDFRONT_DJANGO_LOG_FILE")

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
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
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
