from django.contrib.messages import constants as messages

#------------------------------------------------------------------------------
# ColdFront logging config
#------------------------------------------------------------------------------

from coldfront.config.env import ENV
FILE_OUTPUT = ENV.str('FILE_OUTPUT', default="/tmp/debug.log")
LOG_LEVEL = ENV.str('LOG_LEVEL', default="DEBUG")

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
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        # 'file': {
        #     'class': 'logging.FileHandler',
        #     'filename': FILE_OUTPUT,
        # },
    },
    'loggers': {
        'django_auth_ldap': {
            'level': 'WARN',
            # 'handlers': ['console', 'file'],
            'handlers': ['console', ],
        },
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
        },
    },
}
