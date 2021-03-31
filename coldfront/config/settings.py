"""
Default Django settings for ColdFront project.
"""
import coldfront
import os
import sys
from decimal import Decimal

from django.contrib.messages import constants as messages

# ------------------------------------------------------------------------------
# Django config for ColdFront
# ------------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ALLOWED_HOSTS = ['*']

# ------------------------------------------------------------------------------
# Django Apps
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]


# Additional Apps
INSTALLED_APPS += [
    'crispy_forms',
    'sslserver',
    'django_q',
    'simple_history',
    'durationwidget',
]

# ColdFront Apps
INSTALLED_APPS += [
    'coldfront.core.user',
    'coldfront.core.field_of_science',
    'coldfront.core.utils',
    'coldfront.core.portal',
    'coldfront.core.project',
    'coldfront.core.resource',
    'coldfront.core.allocation',
    # 'coldfront.core.grant',
    # 'coldfront.core.publication',
    # 'coldfront.core.research_output',
    'coldfront.core.statistics',
]

# REST API
INSTALLED_APPS += [
    'rest_framework',
    'django_filters',
    'drf_yasg',
    'coldfront.api',
]

# Savio-specific Additional Apps
INSTALLED_APPS += [
    'formtools',
]

# ------------------------------------------------------------------------------
# Django Middleware
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Database settings
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'coldfront.db'),
    }
}

# ------------------------------------------------------------------------------
# Authentication backends
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.AllowAllUsersModelBackend',
]

#------------------------------------------------------------------------------
# Authentication validators
#------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

#------------------------------------------------------------------------------
# Django site settings
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'coldfront.config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'site/templates'),
            '/usr/share/coldfront/site/templates',
            os.path.join(BASE_DIR, 'coldfront/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_settings_export.settings_export',
            ],
        },
    },
]

SESSION_COOKIE_AGE = 60 * 15
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = 'Strict'

WSGI_APPLICATION = 'coldfront.config.wsgi.application'

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
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'coldfront/static'),
]

# Add local site static files
if os.path.isdir(os.path.join(BASE_DIR, 'site/static')):
    STATICFILES_DIRS.insert(0, os.path.join(BASE_DIR, 'site/static'))

# Add system site static files
if os.path.isdir('/usr/share/coldfront/site/static'):
    STATICFILES_DIRS.insert(0, '/usr/share/coldfront/site/static')

LOGIN_URL = '/user/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SU_LOGIN_CALLBACK = "coldfront.core.utils.common.su_login_callback"
SU_LOGOUT_REDIRECT_URL = "/admin/auth/user/"


SETTINGS_EXPORT = []

# ------------------------------------------------------------------------------
# Data import settings
# ------------------------------------------------------------------------------

# The credentials needed to read from Google Sheets.
GOOGLE_OAUTH2_KEY_FILE = ""

# ------------------------------------------------------------------------------
# REST API settings
# ------------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'coldfront.api.user.authentication.ExpiringTokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.PageNumberPagination'),
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# The number of hours for which a newly created authentication token will be
# valid.
TOKEN_EXPIRATION_HOURS = 24

# ------------------------------------------------------------------------------
# Accounting settings
# ------------------------------------------------------------------------------

# Allocation-related fields can have at most 11 digits and 2 decimal places.
DECIMAL_MAX_DIGITS = 11
DECIMAL_MAX_PLACES = 2

# The minimum and maximum valid numbers of service units for allocations.
ALLOCATION_MIN = Decimal('0.00')
ALLOCATION_MAX = Decimal('100000000.00')

# For accounting purposes, the year begins on June 1st and ends on May 31st.
ALLOCATION_YEAR_START_MONTH = 6
ALLOCATION_YEAR_START_DAY = 1

# The default amount of service units to allocate to Savio projects.
CO_DEFAULT_ALLOCATION = ALLOCATION_MAX
FCA_DEFAULT_ALLOCATION = Decimal('300000.00')
PCA_DEFAULT_ALLOCATION = Decimal('200000.00')

# Whether or not to allow all jobs, bypassing all checks.
ALLOW_ALL_JOBS = False

# ------------------------------------------------------------------------------
# myBRC settings
# ------------------------------------------------------------------------------

# The username of the user to set as the PI for all Vector projects.
VECTOR_PI_USERNAME = "channsoden@berkeley.edu"

# ------------------------------------------------------------------------------
# Local settings overrides (see local_settings.py.sample)
# ------------------------------------------------------------------------------
try:
    from coldfront.config.local_strings import *
except ImportError:
    print("local_strings.py file is required. Copy coldfront/config/local_strings.py.sample to local_strings.py")
    sys.exit()

try:
    from coldfront.config.local_settings import *
except ImportError:
    print("local_settings.py file is required. Copy coldfront/config/local_settings.py.sample to local_settings.py")
    sys.exit()

try:
    INSTALLED_APPS = INSTALLED_APPS + EXTRA_APPS
except NameError:
    INSTALLED_APPS = INSTALLED_APPS

try:
    MIDDLEWARE = MIDDLEWARE + EXTRA_MIDDLEWARE
except NameError:
    MIDDLEWARE = MIDDLEWARE

try:
    AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS + EXTRA_AUTHENTICATION_BACKENDS
except NameError:
    AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS


if 'django_su.backends.SuBackend' in EXTRA_AUTHENTICATION_BACKENDS:
    INSTALLED_APPS.insert(0, 'django_su')
    TEMPLATES[0]['OPTIONS']['context_processors'].extend(['django_su.context_processors.is_su', ])

VERSION = coldfront.__version__

try:
    SETTINGS_EXPORT = SETTINGS_EXPORT + LOCAL_SETTINGS_EXPORT
except NameError:
    SETTINGS_EXPORT = SETTINGS_EXPORT
