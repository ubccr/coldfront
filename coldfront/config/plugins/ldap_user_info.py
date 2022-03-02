from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV


INSTALLED_APPS += [
    'coldfront.plugins.ldap_user_info',
]

#------------------------------------------------------------------------------
# This enables searching for user info via LDAP
#------------------------------------------------------------------------------

LDAP_USER_SEARCH_SERVER_URI = ENV.str('LDAP_USER_SEARCH_SERVER_URI')
LDAP_USER_SEARCH_BASE = ENV.str('LDAP_USER_SEARCH_BASE')
LDAP_USER_SEARCH_BIND_DN = ENV.str('LDAP_USER_SEARCH_BIND_DN')
LDAP_USER_SEARCH_BIND_PASSWORD = ENV.str('LDAP_USER_SEARCH_BIND_PASSWORD')
