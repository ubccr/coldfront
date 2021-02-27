from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [
    'coldfront.plugins.slurm',
]

SLURM_SACCTMGR_PATH = '/usr/bin/sacctmgr'
SLURM_NOOP = False
SLURM_IGNORE_USERS = ['root']

# SLURM_IGNORE_ACCOUNTS = ['staff', 'admins']
