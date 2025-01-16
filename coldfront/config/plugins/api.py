from coldfront.config.base import INSTALLED_APPS

INSTALLED_APPS += [
        'django_filters',
        'rest_framework',
        'rest_framework.authtoken',
        'oauth2_provider',
        'coldfront.plugins.api'
        ]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        # only use BasicAuthentication for test purposes
        # 'rest_framework.authentication.BasicAuthentication',
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
}
