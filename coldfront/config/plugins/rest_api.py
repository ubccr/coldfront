from coldfront.config.base import INSTALLED_APPS, ENV
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# REST API site settings
#------------------------------------------------------------------------------

# Additional Apps
INSTALLED_APPS += [
    'rest_framework',
    'rest_framework.authtoken',
    'oauth2_provider',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
      
    ]
}


INSTALLED_APPS += [
    'coldfront.plugins.rest_api',
]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
       'rest_framework.permissions.IsAuthenticated'
       #'coldfront.icm.rest.permissions.api.GlobalReadOnly'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',     
    ]    
}