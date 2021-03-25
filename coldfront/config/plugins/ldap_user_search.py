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
ADDITIONAL_USER_SEARCH_CLASSES = ['coldfront.plugins.ldap_user_search.utils.LDAPUserSearch',]
