
#------------------------------------------------------------------------------
# General Center Information
#------------------------------------------------------------------------------
CENTER_NAME = 'Berkeley Research Computing'
CENTER_HELP_URL = 'https://docs-research-it.berkeley.edu/services/high-performance-computing/getting-help/'
CENTER_PROJECT_RENEWAL_HELP_URL = 'https://docs-research-it.berkeley.edu/services/high-performance-computing/getting-help/'
#CENTER_BASE_URL = 'https://docs-research-it.berkeley.edu/services/high-performance-computing/'
CENTER_BASE_URL = 'https://coldfront.io/'

#------------------------------------------------------------------------------
# Email/Notification settings
#------------------------------------------------------------------------------
EMAIL_ENABLED = True
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/root/coldfront_app/coldfront_emails/'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
EMAIL_TIMEOUT = 3
EMAIL_SUBJECT_PREFIX = '[myBRC]'
EMAIL_ADMIN_LIST = ['admin@localhost']
EMAIL_SENDER = 'coldfront@localhost'
EMAIL_TICKET_SYSTEM_ADDRESS = 'help@localhost'
EMAIL_DIRECTOR_EMAIL_ADDRESS = 'director@localhost'
EMAIL_PROJECT_REVIEW_CONTACT = 'review@localhost'
EMAIL_DEVELOPMENT_EMAIL_LIST = ['dev1@localhost', 'dev2@localhost']
EMAIL_OPT_OUT_INSTRUCTION_URL = 'http://localhost/optout'
EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS = [7, 14, 30]
EMAIL_SIGNATURE = """
HPC Resources
http://localhost
"""

GOOGLE_OAUTH2_KEY_FILE = "/root/coldfront_app/coldfronttestvmaccess-494b1e3d64df.json"
SESSION_COOKIE_AGE = 60 * 120
