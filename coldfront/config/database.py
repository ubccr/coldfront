import os
import sys
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Database settings
#------------------------------------------------------------------------------
# Set this using the DB_URL env variable. Defaults to sqlite.
#
# Examples:
#
# MariaDB:
#  DB_URL=mysql://user:password@127.0.0.1:3306/database
#
# Postgresql:
#  DB_URL=psql://user:password@127.0.0.1:5432/database
#------------------------------------------------------------------------------

DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.mysql',
         'NAME': ENV.str('DB', default="coldfront"),
         'USER': ENV.str('DB_USER'),
         'PASSWORD': ENV.str('DB_PASS'),
         'HOST': ENV.str('DB_HOST', default="127.0.0.1"),
         'PORT': '3306',
     },
    'default': ENV.db_url(
        var='DB_URL',
        default='sqlite:///' + os.path.join(os.getcwd(), 'coldfront.db')
    )
}

# Covers regular testing and django-coverage
if 'test' in sys.argv or 'test_coverage' in sys.argv:
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'



#------------------------------------------------------------------------------
# Custom Database settings
#------------------------------------------------------------------------------
# You can also override this manually in local_settings.py, for example:
#
# NOTE: For mysql you need to: pip install mysqlclient
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'coldfront',
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '',
#     },
# }
#
# NOTE: For postgresql you need to: pip install psycopg2
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'coldfront',
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     },
# }
