# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.messages import constants as messages

# ------------------------------------------------------------------------------
# ColdFront logging config
# ------------------------------------------------------------------------------

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
        # 'file': {
        #     'class': 'logging.FileHandler',
        #     'filename': '/tmp/debug.log',
        # },
    },
    "loggers": {
        "django_auth_ldap": {
            "level": "WARNING",
            # 'handlers': ['console', 'file'],
            "handlers": [
                "console",
            ],
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
