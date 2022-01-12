from coldfront.config.env import ENV
from django.core.exceptions import ImproperlyConfigured

try:
    import ldap
except ImportError:
    raise ImproperlyConfigured('Please run: pip install ldap3')

#------------------------------------------------------------------------------
# This enables searching for users via LDAP
#------------------------------------------------------------------------------

LDAP_USER_SEARCH_SERVER_URI = ENV.str('LDAP_USER_SEARCH_SERVER_URI')
LDAP_USER_SEARCH_BASE = ENV.str('LDAP_USER_SEARCH_BASE')
LDAP_USER_SEARCH_BIND_DN = ENV.str('LDAP_USER_SEARCH_BIND_DN')
LDAP_USER_SEARCH_BIND_PASSWORD = ENV.str('LDAP_USER_SEARCH_BIND_PASSWORD')
LDAP_USER_SEARCH_CONNECT_TIMEOUT = ENV.float('LDAP_USER_SEARCH_CONNECT_TIMEOUT', default=2.5)
LDAP_USER_SEARCH_USE_SSL = ENV.bool('LDAP_USER_SEARCH_USE_SSL', default=True)
ADDITIONAL_USER_SEARCH_CLASSES = ['coldfront.plugins.ldap_user_search.utils.LDAPUserSearch',]
