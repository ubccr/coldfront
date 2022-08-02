from coldfront.config.env import ENV
from coldfront.config.base import AUTHENTICATION_BACKENDS
from django.core.exceptions import ImproperlyConfigured

if ENV.bool('PLUGIN_ORCID', default=False):

    try:
        import orcid
    except ImportError:
        raise ImproperlyConfigured('Please run: pip install orcid')


    ORCID_CLIENT_ID = ENV.str('ORCID_CLIENT_ID', default='')
    ORCID_CLIENT_SECRET = ENV.str('ORCID_CLIENT_SECRET', default='')
    ORCID_REDIRECT = ENV.str('ORCID_REDIRECT', default='')
    ORCID_SANDBOX= ENV.bool('ORCID_SANDBOX', default=False)
    