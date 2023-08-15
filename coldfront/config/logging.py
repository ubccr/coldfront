from django.contrib.messages import constants as messages
from coldfront.config.env import ENV

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

LOGGING_FILE = ENV.str('LOGGING_FILE', default=None)
LOGGING_VERSION = ENV.int('LOGGING_VERSION', default=1)


LOGGING = {
    'version': LOGGING_VERSION,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': LOGGING_FILE,
        },
    },
    'loggers': {
        'django_auth_ldap': {
            'level': 'WARN',
            # 'handlers': ['console', 'file'],
            'handlers': ['console', ],
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
