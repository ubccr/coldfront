from coldfront.config.base import INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Enable Mokey/Hydra OpenID Connect Authentication Backend
#------------------------------------------------------------------------------
INSTALLED_APPS += [
    'mozilla_django_oidc',
    'coldfront.plugins.mokey_oidc',
]

AUTHENTICATION_BACKENDS += [
    'coldfront.plugins.mokey_oidc.auth.OIDCMokeyAuthenticationBackend',
]

MIDDLEWARE += [
    'mozilla_django_oidc.middleware.SessionRefresh',
]

OIDC_OP_JWKS_ENDPOINT = ENV.str('OIDC_OP_JWKS_ENDPOINT')
OIDC_RP_SIGN_ALGO = ENV.str('OIDC_RP_SIGN_ALGO')
OIDC_RP_CLIENT_ID = ENV.str('OIDC_RP_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = ENV.str('OIDC_RP_CLIENT_SECRET')
OIDC_OP_AUTHORIZATION_ENDPOINT = ENV.str('OIDC_OP_AUTHORIZATION_ENDPOINT')
OIDC_OP_TOKEN_ENDPOINT = ENV.str('OIDC_OP_TOKEN_ENDPOINT')
OIDC_OP_USER_ENDPOINT = ENV.str('OIDC_OP_USER_ENDPOINT')
OIDC_VERIFY_SSL = ENV.bool('OIDC_VERIFY_SSL', default=True)
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = ENV.int('OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS', default=3600)
