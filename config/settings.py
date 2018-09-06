"""
Default Django settings for Coldfront project.
"""
import os
import sys

from django.contrib.messages import constants as messages

# ------------------------------------------------------------------------------
# Default Django config
# ------------------------------------------------------------------------------


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = ['*']


# Djgano Application definition


# Django Apps

DEFAULT_INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]


# Additional Apps
DEFAULT_INSTALLED_APPS += [
    'crispy_forms',
    'sslserver',
    'social_django',
    'admin_comments',
    'django_q',
    'hijack',
    'hijack_admin',
    'compat',
    'simple_history',
]

# Coldfront Apps
DEFAULT_INSTALLED_APPS += [
    'common.djangoapps.common',
    'common.djangoapps.user',
    'common.djangoapps.field_of_science',
    'common.djangoapps.utils',
    'core.djangoapps.portal',
    'core.djangoapps.project',
    'core.djangoapps.resources',
    'core.djangoapps.subscription',
    'core.djangoapps.grant',
    'core.djangoapps.publication',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'site/templates'),
            os.path.join(BASE_DIR, 'common/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


SESSION_COOKIE_AGE = 60 * 60

WSGI_APPLICATION = 'config.wsgi.application'

USE_I18N = True
USE_L10N = True
USE_TZ = True

ADMIN_COMMENTS_SHOW_EMPTY = True

MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

CRISPY_TEMPLATE_PACK = 'bootstrap4'

STATIC_URL = '/static/'
STATIC_ROOT = './static_root/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'site/static'),
    os.path.join(BASE_DIR, 'static'),
)

LOGIN_URL = '/user/login'
LOGIN_REDIRECT_URL = '/'

HIJACK_USE_BOOTSTRAP = True
HIJACK_ALLOW_GET_REQUESTS = True

#------------------------------------------------------------------------------
# Local settings overrides
#------------------------------------------------------------------------------
try:
    from config.local_strings import *
except ImportError:
    print("local_strings.py file is required. Copy local_strings.py.sample to local_strings.py")
    sys.exit()

try:
    from config.local_settings import *
except ImportError:
    print("local_settings.py file is required. Copy local_settings.py.sample to local_settings.py")
    sys.exit()

try:
    INSTALLED_APPS = DEFAULT_INSTALLED_APPS + EXTRA_APPS
except NameError:
    INSTALLED_APPS = DEFAULT_INSTALLED_APPS

try:
    AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS + tuple(EXTRA_AUTHENTICATION_BACKENDS)
except NameError:
    AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS

if 'extra.djangoapps.mokey_odic' in EXTRA_APPS:
    # INSTALLED_APPS.append('social_django')
    TEMPLATES['OPTIONS']['context_processors'].extend(['social_django.context_processors.backends',
                                                       'social_django.context_processors.login_redirect', ])
