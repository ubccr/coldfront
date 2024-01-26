from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING

INSTALLED_APPS += [
    'coldfront.plugins.slurm',
]

SLURM_SACCTMGR_PATH = ENV.str('SLURM_SACCTMGR_PATH', default='/usr/bin/sacctmgr')
SLURM_NOOP = ENV.bool('SLURM_NOOP', False)
SLURM_IGNORE_USERS = ENV.list('SLURM_IGNORE_USERS', default=['root'])
SLURM_IGNORE_ACCOUNTS = ENV.list('SLURM_IGNORE_ACCOUNTS', default=[])


LOGGING['handlers']['slurm'] = {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/slurm.log',
            'when': 'D',
            'backupCount': 10, # how many backup files to keep
            'formatter': 'default',
            'level': 'DEBUG',
        }

LOGGING['loggers']['coldfront.plugins.slurm'] = {
            'handlers': ['slurm'],
        }
