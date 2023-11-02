from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Enable XDMoD support
#------------------------------------------------------------------------------
INSTALLED_APPS += [
    'coldfront.plugins.xdmod',
]

XDMOD_USER = ENV.str('XDMOD_USER', default='')
XDMOD_PASS = ENV.str('XDMOD_PASS', default='')
XDMOD_API_URL = ENV.str('XDMOD_API_URL')
