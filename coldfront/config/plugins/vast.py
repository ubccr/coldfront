from coldfront.config.env import ENV
from coldfront.config.base import INSTALLED_APPS

VASTUSER = ENV.str('VASTUSER', default=None)
VASTPASS = ENV.str('VASTPASS', default=None)
VASTTOKEN = ENV.str('VASTTOKEN', default=None)
VASTADDRESS = ENV.str('VASTADDRESS', default=None)
VASTAPI = ENV.str('VASTAPI', default='v6')
VASTAUTHORIZER = ENV.str('VASTAUTHORIZER', default='AD')

INSTALLED_APPS += [ 'coldfront.plugins.vast' ]
