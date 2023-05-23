from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    'coldfront.plugins.slate_project_info',
]

LDAP_SLATE_PROJECT_SERVER_URI = ENV.str('LDAP_SLATE_PROJECT_SERVER_URI')
LDAP_SLATE_PROJECT_USER_SEARCH_BASE = ENV.str('LDAP_SLATE_PROJECT_USER_SEARCH_BASE')