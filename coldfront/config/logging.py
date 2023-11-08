from django.contrib.messages import constants as messages

#------------------------------------------------------------------------------
# ColdFront logging config
#------------------------------------------------------------------------------

MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'key-events': {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {levelname} {message}",
            "style": "{",
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'django-q': {
            'class': 'logging.FileHandler',
            'filename': 'django-q.log',
        },
        'key-events': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/key-events.log',
            'when': 'D',
            'formatter': 'key-events',
        },
        # 'file': {
        #     'class': 'logging.FileHandler',
        #     'filename': '/tmp/debug.log',
        # },
    },
    'loggers': {
        'django_auth_ldap': {
            'level': 'INFO',
            # 'handlers': ['console', 'file'],
            'handlers': ['console', ],
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django-q': {
            'handlers': ['django-q'],
            'level': 'DEBUG',
        },
        'ifx': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'ifxbilling': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'coldfront.core.project': {
            'handlers': ['key-events'],
            'level': 'INFO',
        },
        'coldfront.core.allocation': {
            'handlers': ['key-events'],
            'level': 'INFO',
        }
    },
}
