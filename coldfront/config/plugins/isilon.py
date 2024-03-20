from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [ 'coldfront.plugins.isilon' ]
ISILON_USER = ENV.str('ISILON_USER', '')
ISILON_PASS = ENV.str('ISILON_PASS', '')

ISILON_NFS_ROOT_CLIENTS = ENV.str('ISILON_NFS_ROOT_CLIENTS', '')
ISILON_NFS_FASSE_CLIENTS = ENV.str('ISILON_NFS_FASSE_CLIENTS', '')
ISILON_NFS_CANNON_CLIENTS = ENV.str('ISILON_NFS_CANNON_CLIENTS', '')
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

ISILON_AUTH_MODEL = 'ldap'
