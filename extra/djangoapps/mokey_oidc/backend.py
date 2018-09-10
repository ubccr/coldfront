

from jwkest.jwk import KEYS
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.utils import cache

from common.djangolibs.utils import import_from_settings


class Mokey_Oidc(OpenIdConnectAuth):
    """Mokey OpenID Connect authentication backend"""

    # Override OIDC_ENDPOINT in your subclass to enable autoconfig of OIDC
    name = 'mokey_oidc'

    OIDC_ENDPOINT = None
    ID_TOKEN_MAX_AGE = 600
    DEFAULT_SCOPE = ''
    EXTRA_DATA = None
    REDIRECT_STATE = False
    ACCESS_TOKEN_METHOD = 'POST'
    REVOKE_TOKEN_METHOD = 'GET'
    ID_KEY = 'sub'
    USERNAME_KEY = 'uid'
    ID_TOKEN_ISSUER = ''
    ACCESS_TOKEN_URL = ''
    AUTHORIZATION_URL = ''
    REVOKE_TOKEN_URL = ''
    USERINFO_URL = ''
    JWKS_URI = ''

    def __init__(self, *args, **kwargs):
        super(OpenIdConnectAuth, self).__init__(*args, **kwargs)

        """Initialize settings."""

        """Overwrite defaults."""
        self.OIDC_ENDPOINT = import_from_settings(
            'SOCIAL_AUTH_MOKEY_OIDC_ENDPOINT')
        self.DEFAULT_SCOPE = import_from_settings(
            'SOCIAL_AUTH_MOKEY_OIDC_DEFAULT_SCOPE')

        """CCR specific settings."""
        self.OIDC_CA_CERT = import_from_settings(
            'SOCIAL_AUTH_MOKEY_OIDC_VERIFY_SSL')

    def auth_complete_credentials(self):
        """Here we assume the token endpoint authentication method is
        client_secret_post so we don't send basic auth creds
        """
        return None

    @cache(ttl=86400)
    def get_jwks_keys(self):
        keys = KEYS()
        keys.load_from_url(self.jwks_uri(), verify=self.OIDC_CA_CERT)
        return keys

    def user_data(self, access_token, *args, **kwargs):
        """ Mokey Open ID connect does not use the user endpoint, so return id_token."""
        return self.id_token

    def get_user_details(self, response):
        username_key = self.setting('USERNAME_KEY', default=self.USERNAME_KEY)

        return {
            'username': response.get(username_key),
            'email': response.get('email'),
            'first_name': response.get('first'),
            'last_name': response.get('last'),
        }
