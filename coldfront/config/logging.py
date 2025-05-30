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

FILE_ENABLE = ENV.bool('FILE_ENABLE', default=False)
LOG_LEVEL = ENV.str('LOG_LEVEL', default="INFO")
LOG_LEVEL_LDAP = ENV.str('LOG_LEVEL_LDAP', default=LOG_LEVEL)
LOGGING_FILE = ENV.str('LOGGING_FILE', default="/tmp/debug.log")
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
            'level': LOG_LEVEL_LDAP,
            # 'handlers': ['console', 'file'],
            'handlers': ['console', ],
        },
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
        },
    },
}
