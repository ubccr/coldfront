"""
Base Django settings for ColdFront project.
"""
import os
import sys
import coldfront
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from coldfront.config.env import ENV, PROJECT_ROOT

#------------------------------------------------------------------------------
# Base Django config for ColdFront
#------------------------------------------------------------------------------
VERSION = coldfront.VERSION
BASE_DIR = PROJECT_ROOT()
ALLOWED_HOSTS = ENV.list('ALLOWED_HOSTS', default=['*'])
CSRF_TRUSTED_ORIGINS = ['http://localhost', 'https://*.rc.fas.harvard.edu']
DEBUG = ENV.bool('DEBUG', default=False)
WSGI_APPLICATION = 'coldfront.config.wsgi.application'
ROOT_URLCONF = 'coldfront.config.urls'

SECRET_KEY = ENV.str('SECRET_KEY', default='')
if len(SECRET_KEY) == 0:
    SECRET_KEY = get_random_secret_key()

#------------------------------------------------------------------------------
# Locale settings
#------------------------------------------------------------------------------
LANGUAGE_CODE = ENV.str('LANGUAGE_CODE', default='en-us')
TIME_ZONE = ENV.str('TIME_ZONE', default='America/New_York')
USE_I18N = True
USE_L10N = True
USE_TZ = True

#------------------------------------------------------------------------------
# Django Apps
#------------------------------------------------------------------------------

# See: https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
# We should change this to BigAutoField at some point
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_tables2',
    'table',
    'rest_framework_datatables',
    'easy_pdf',
]

# Additional Apps
# Hack to fix fontawesome. Will be fixed in version 6
sys.modules['fontawesome_free'] = __import__('fontawesome-free')
INSTALLED_APPS += [
    'crispy_forms',
    'crispy_bootstrap4',
    'sslserver',
    'django_q',
    'simple_history',
    'fontawesome_free',
    'mathfilters',
    # 'debug_toolbar',
    # 'ifxuser',
    # 'author',
    # 'ifxbilling',
    # 'ifxreport',
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
    'coldfront.core.grant',
    'coldfront.core.department',
    'coldfront.core.publication',
    'coldfront.core.research_output',
    'coldfront.plugins.ifx',
    'coldfront.core.test_helpers'
]


#------------------------------------------------------------------------------
# Django Middleware
#------------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]
MIDDLEWARE += [
    'author.middlewares.AuthorDefaultBackendMiddleware',
]


#------------------------------------------------------------------------------
# Django authentication backend. See auth.py
#------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = []


#------------------------------------------------------------------------------
# Django template and site settings
#------------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            PROJECT_ROOT('site/templates'),
            '/usr/share/coldfront/site/templates',
            PROJECT_ROOT('coldfront/templates'),
            '/usr/local/lib/python3.10/site-packages/rest_framework/templates',
            '/usr/local/lib/python3.10/site-packages/crispy_bootstrap4/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_settings_export.settings_export',
                'django.template.context_processors.request',
                'coldfront.config.context_processors.export_vars',
            ],
            'libraries': {
                'rest_framework': 'rest_framework.templatetags.rest_framework',
            },
        },
    },
]

# Add local site templates files if set
SITE_TEMPLATES = ENV.str('SITE_TEMPLATES', default='')
if len(SITE_TEMPLATES) > 0:
    if os.path.isdir(SITE_TEMPLATES):
        TEMPLATES[0]['DIRS'].insert(0, SITE_TEMPLATES)
    else:
        raise ImproperlyConfigured('SITE_TEMPLATES should be a path to a directory')

CRISPY_TEMPLATE_PACK = 'bootstrap4'
SETTINGS_EXPORT = ['INSTALLED_APPS']

STATIC_URL = '/static/'
STATIC_ROOT = ENV.str('STATIC_ROOT', default=PROJECT_ROOT('static_root'))
STATICFILES_DIRS = [
   PROJECT_ROOT('coldfront/static'),
]
# COLDFRONT_DATA_LOAD = ENV.str(‘COLDFRONT_DATA_LOAD’, default=PROJECT_ROOT(‘local_data’))

# Add local site static files if set
SITE_STATIC = ENV.str('SITE_STATIC', default='')
if len(SITE_STATIC) > 0:
    if os.path.isdir(SITE_STATIC):
        STATICFILES_DIRS.insert(0, SITE_STATIC)
    else:
        raise ImproperlyConfigured('SITE_STATIC should be a path to a directory')

# Add system site static files
if os.path.isdir('/usr/share/coldfront/site/static'):
    STATICFILES_DIRS.insert(0, '/usr/share/coldfront/site/static')


DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
