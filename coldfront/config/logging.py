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
        'custom': {
            'format': '{levelname} {asctime} {message}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': './coldfront.log',
            'formatter': 'custom'
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    }
    #'loggers': {
    #    'django_auth_ldap': {
    #        'level': 'WARN',
    #        # 'handlers': ['console', 'file'],
    #        'handlers': ['console', ],
    #    },
    #    'django': {
    #        'handlers': ['console'],
    #        'level': 'INFO',
    #    },
    #    'root': {
    #        'handlers': ['console', 'file'],
    #        'level': 'INFO',
    #    }
    #},
}
