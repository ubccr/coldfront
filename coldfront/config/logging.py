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
            "format": "[{server_time}] {name} {levelname} {message}",
            "style": "{",
        },
        'default': {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {name} {levelname} {message}",
            "style": "{",
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'django-q': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/django-q.log',
            'when': 'midnight',
            'backupCount': 10,
            'formatter': 'key-events',
            'level': 'DEBUG',
        },
        'key-events': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/key-events.log',
            'when': 'midnight',
            'backupCount': 10,
            'formatter': 'key-events',
            'level': 'INFO',
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
            'handlers': ['django-q', 'key-events'],
        },
        'ifx': {
            'handlers': ['console', 'key-events'],
            'level': 'INFO',
        },
        'ifxbilling': {
            'handlers': ['console', 'key-events'],
            'level': 'INFO',
        },
        'coldfront': {
            'handlers': ['key-events'],
            'level': 'INFO',
        },
    },
}
