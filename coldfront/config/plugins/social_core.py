from coldfront.config.base import INSTALLED_APPS, TEMPLATES, AUTHENTICATION_BACKENDS
from coldfront.config.env import ENV

from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path
import importlib

INSTALLED_APPS +=  ['social_django',
]

if ENV.bool('PLUGIN_SOCIAL_CORE', default=False):

    # try:
    #     importlib.import_module('social-auth-app-django')
    # except ImportError:
    #     raise ImproperlyConfigured('Please run: pip install social-auth-app-django')

    TEMPLATES[0]['OPTIONS']['context_processors'].extend(['social_django.context_processors.backends',
                                                'social_django.context_processors.login_redirect',])
    

    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.social_auth.auth_allowed',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
    )

    SOCIAL_AUTH_DISCONNECT_PIPELINE = (
        'social_core.pipeline.disconnect.allowed_to_disconnect',
        'social_core.pipeline.disconnect.get_entries',
        'social_core.pipeline.disconnect.revoke_tokens',
        'social_core.pipeline.disconnect.disconnect',
    )

    if ENV.bool('PLUGIN_ORCID', default=False):

        if ENV.bool('ORCID_SANDBOX', default=False):
            AUTHENTICATION_BACKENDS += ['social_core.backends.orcid.ORCIDOAuth2Sandbox',
            ]

        else:
            AUTHENTICATION_BACKENDS += ['social_core.backends.orcid.ORCIDOAuth2',
            ]

        SOCIAL_AUTH_ORCID_SANDBOX_KEY = ENV.str('ORCID_CLIENT_ID', default='')
        SOCIAL_AUTH_ORCID_SANDBOX_SECRET = ENV.str('ORCID_CLIENT_SECRET', default='')

    SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/user/user-profile/'
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
    SOCIAL_AUTH_URL_NAMESPACE = 'social'



    