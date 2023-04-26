from coldfront.config.base import INSTALLED_APPS
from coldfront.config.logging import LOGGING
from coldfront.config.env import ENV


INSTALLED_APPS += [ 'coldfront.plugins.sftocf' ]

SFUSER = ENV.str('SFUSER')
SFPASS = ENV.str('SFPASS')
STARFISH_SERVER = 'starfish'


LOGGING['formatters']['sftocf'] = {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {levelname} {message}",
            "style": "{",
        }

LOGGING['handlers']['sftocf'] = {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/sftocf.log',
            'when': 'D',
            'backupCount': 30, # how many backup files to keep
            'formatter': 'sftocf',
        }

LOGGING['loggers']['sftocf'] = {
            'handlers': ['sftocf'],
            'level': 'DEBUG',
        }
