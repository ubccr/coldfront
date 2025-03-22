from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Email/Notification settings
#------------------------------------------------------------------------------
EMAIL_ENABLED = ENV.bool('EMAIL_ENABLED', default=False)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = ENV.str('EMAIL_HOST', default='localhost')
EMAIL_PORT = ENV.int('EMAIL_PORT', default=25)
EMAIL_HOST_USER = ENV.str('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = ENV.str('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = ENV.bool('EMAIL_USE_TLS', default=False)
EMAIL_TIMEOUT = ENV.int('EMAIL_TIMEOUT', default=3)
EMAIL_SUBJECT_PREFIX = ENV.str('EMAIL_SUBJECT_PREFIX', default='[ColdFront]')
EMAIL_ADMIN_LIST = ENV.list('EMAIL_ADMIN_LIST', default=[])
EMAIL_SENDER = ENV.str('EMAIL_SENDER', default='')
EMAIL_TICKET_SYSTEM_ADDRESS = ENV.str('EMAIL_TICKET_SYSTEM_ADDRESS', default='')
EMAIL_DIRECTOR_EMAIL_ADDRESS = ENV.str('EMAIL_DIRECTOR_EMAIL_ADDRESS', default='')
EMAIL_PROJECT_REVIEW_CONTACT = ENV.str('EMAIL_PROJECT_REVIEW_CONTACT', default='')
EMAIL_DEVELOPMENT_EMAIL_LIST = ENV.list('EMAIL_DEVELOPMENT_EMAIL_LIST', default=[])
EMAIL_OPT_OUT_INSTRUCTION_URL = ENV.str('EMAIL_OPT_OUT_INSTRUCTION_URL', default='')
EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS = ENV.list('EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS', cast=int, default=[7, 14, 30])
EMAIL_SIGNATURE = ENV.str('EMAIL_SIGNATURE', default='', multiline=True)
EMAIL_RESOURCE_NOTIFICATIONS_ENABLED = ENV.bool('EMAIL_RESOURCE_NOTIFICATIONS_ENABLED', default=False)
EMAIL_RESOURCE_EXPIRING_NOTIFICATION_DAYS = ENV.list('EMAIL_RESOURCE_EXPIRING_NOTIFICATION_DAYS', cast=int, default=[7, 14, 30])
EMAIL_ADMINS_ON_ALLOCATION_EXPIRE = ENV.bool('EMAIL_ADMINS_ON_ALLOCATION_EXPIRE', default=False)
