from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.slurm',
]

SLURM_SACCTMGR_PATH = ENV.str('SLURM_SACCTMGR_PATH', default='/usr/bin/sacctmgr')
SLURM_NOOP = ENV.bool('SLURM_NOOP', False)
SLURM_IGNORE_USERS = ENV.list('SLURM_IGNORE_USERS', default=['root'])
SLURM_IGNORE_ACCOUNTS = ENV.list('SLURM_IGNORE_ACCOUNTS', default=[])
SLURM_SUBMISSION_INFO = ENV.list('SLURM_SUBMISSION_INFO', default=['account'])
SLURM_DISPLAY_SHORT_OPTION_NAMES = ENV.bool('SLURM_DISPLAY_SHORT_OPTION_NAMES', default=False)
SLURM_SHORT_OPTION_NAMES = ENV.dict('SLURM_SHORT_OPTION_NAMES', default={
    'qos': 'q',
    'account': 'A',
    'clusters': 'M',
    'partition': 'p',
})