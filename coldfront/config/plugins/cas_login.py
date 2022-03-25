from coldfront.config.base import AUTHENTICATION_BACKENDS, INSTALLED_APPS, MIDDLEWARE
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'django_cas_ng',
]

if ENV.bool('DEBUG', default=False):
    INSTALLED_APPS += [
        'django_extensions'
    ]

MIDDLEWARE += [
    'django_cas_ng.middleware.CASMiddleware',
]



AUTHENTICATION_BACKENDS += [
    'django_cas_ng.backends.CASBackend',
]


# Base config for CAS login
PLUGIN_CAS = ENV.bool('PLUGIN_CAS', default=True)
CAS_SERVER_URL = ENV.str('CAS_SERVER_URL', default='https://idp-stg.login.iu.edu/idp/profile/cas/')
CAS_VERSION = ENV.str('CAS_VERSION', default='2')
CAS_LOGOUT_COMPLETELY = ENV.bool('CAS_LOGOUT_COMPLETELY', default=False)
CAS_AUTO_CREATE_USERS = ENV.bool('CAS_AUTO_CREATE_USERS', default=True)
CAS_LOGIN_URL_NAME = 'login'
CAS_LOGOUT_URL_NAME = 'logout'
CAS_REDIRECT_URL = '/'
#CAS_STORE_NEXT = True