from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += ['coldfront.plugins.lfs']

LFS_HOST = ENV.str('LFS_HOST', default='localhost')
LFS_PORT = ENV.int('LFS_PORT', default=50051)
