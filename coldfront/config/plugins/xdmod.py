from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING

#------------------------------------------------------------------------------
# Enable XDMoD support
#------------------------------------------------------------------------------
INSTALLED_APPS += [
    'coldfront.plugins.xdmod',
]

XDMOD_USER = ENV.str('XDMOD_USER', default='')
XDMOD_PASS = ENV.str('XDMOD_PASS', default='')
XDMOD_API_URL = ENV.str('XDMOD_API_URL')


LOGGING['formatters']['xdmod'] = {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {levelname} {message}",
            "style": "{",
        }

LOGGING['handlers']['xdmod'] = {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/xdmod.log',
            'when': 'D',
            'backupCount': 30, # how many backup files to keep
            'formatter': 'xdmod',
        }

LOGGING['loggers']['xdmod'] = {
            'handlers': ['xdmod'],
            'level': 'INFO',
        }
