from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.scale_management'
]

# SCALE_MAN_ENDPOINT = ENV.str('SYSMON_ENDPOINT')
