from coldfront.config.env import ENV
from coldfront.config.base import INSTALLED_APPS, AUTHENTICATION_BACKENDS, TEMPLATES

#------------------------------------------------------------------------------
# ColdFront default authentication settings
#------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS += [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/user/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = ENV.str('LOGOUT_REDIRECT_URL', LOGIN_URL)

SU_LOGIN_CALLBACK = "coldfront.core.utils.common.su_login_callback"
SU_LOGOUT_REDIRECT_URL = "/admin/auth/user/"

SESSION_COOKIE_AGE = 60 * 15
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SECURE = True

#------------------------------------------------------------------------------
# Enable administrators to login as other users
#------------------------------------------------------------------------------
if ENV.bool('ENABLE_SU', default=True):
    AUTHENTICATION_BACKENDS += ['django_su.backends.SuBackend', ]
    INSTALLED_APPS.insert(0, 'django_su')
    TEMPLATES[0]['OPTIONS']['context_processors'].extend(['django_su.context_processors.is_su', ])
