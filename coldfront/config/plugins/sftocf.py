from coldfront.config.base import INSTALLED_APPS
from coldfront.config.logging import LOGGING
from coldfront.config.env import ENV


INSTALLED_APPS += [ 'coldfront.plugins.sftocf' ]

SFUSER = ENV.str('SFUSER')
SFPASS = ENV.str('SFPASS')
STARFISH_SERVER = ENV.str('STARFISH_SERVER')


LOGGING['handlers']['sftocf'] = {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/sftocf.log',
            'when': 'D',
            'backupCount': 10, # how many backup files to keep
            'formatter': 'default',
            'level': 'DEBUG',
        }

LOGGING['loggers']['coldfront.plugins.sftocf'] = {
            'handlers': ['sftocf'],
        }
