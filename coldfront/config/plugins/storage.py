from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.storage',
]

#VARIABLE = ENV.str('VARIABLE', default='variable')
