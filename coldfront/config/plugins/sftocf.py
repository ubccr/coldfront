from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [ 'coldfront.plugins.sftocf' ]

SFUSER = ENV.str('SFUSER')
SFPASS = ENV.str('SFPASS')
