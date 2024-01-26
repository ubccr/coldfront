"""
FASRC-specific LDAP plugin settings
"""
from django.core.exceptions import ImproperlyConfigured

from coldfront.config.env import ENV
from coldfront.config.logging import LOGGING
from coldfront.config.base import INSTALLED_APPS

try:
    import ldap3
    from django_auth_ldap.config import GroupOfNamesType, LDAPSearch
except ImportError as exc:
    raise ImproperlyConfigured('Please run: pip install ldap3') from exc

INSTALLED_APPS += [ 'coldfront.plugins.ldap' ]

AUTH_LDAP_SERVER_URI = ENV.str('AUTH_LDAP_SERVER_URI')
AUTH_LDAP_BIND_DN = ENV.str('AUTH_LDAP_BIND_DN')
AUTH_LDAP_BIND_PASSWORD = ENV.str('AUTH_LDAP_BIND_PASSWORD')
AUTH_LDAP_USER_SEARCH_BASE = ENV.str('AUTH_LDAP_USER_SEARCH_BASE')
AUTH_LDAP_GROUP_SEARCH_BASE = ENV.str('AUTH_LDAP_GROUP_SEARCH_BASE')


LOGGING['handlers']['ldap_fasrc'] = {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/ldap_fasrc.log',
            'backupCount': 10,
            'when': 'midnight',
            'formatter': 'default',
            'level': 'DEBUG',
        }

LOGGING['loggers']['coldfront.plugins.ldap'] = {
            'handlers': ['ldap_fasrc'],
        }
