from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING
from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [ 'coldfront.plugins.isilon' ]
ISILON_USER = ENV.str('ISILON_USER')
ISILON_PASS = ENV.str('ISILON_PASS')

