from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [ 'coldfront.plugins.isilon' ]
ISILON_USER = ENV.str('ISILON_USER', '')
ISILON_PASS = ENV.str('ISILON_PASS', '')

LOGGING['handlers']['isilon'] = {
    'class': 'logging.handlers.TimedRotatingFileHandler',
    'filename': 'logs/isilon.log',
    'when': 'D',
    'backupCount': 10, # how many backup files to keep
    'formatter': 'default',
    'level': 'DEBUG',
}

LOGGING['loggers']['coldfront.plugins.isilon'] = {
    'handlers': ['isilon'],
}
