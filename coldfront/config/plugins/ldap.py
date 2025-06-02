# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.exceptions import ImproperlyConfigured

from coldfront.config.base import AUTHENTICATION_BACKENDS
from coldfront.config.env import ENV

try:
    import ldap
    from django_auth_ldap.config import GroupOfNamesType, LDAPSearch
except ImportError:
    raise ImproperlyConfigured("Please run: pip install ldap3 django_auth_ldap")

# ------------------------------------------------------------------------------
# LDAP user authentication using django-auth-ldap.  This will enable LDAP
# user/password logins. You can also override this in local_settings.py
# ------------------------------------------------------------------------------
AUTH_COLDFRONT_LDAP_SEARCH_SCOPE = ENV.str("AUTH_COLDFRONT_LDAP_SEARCH_SCOPE", default="ONELEVEL")

AUTH_LDAP_SERVER_URI = ENV.str("AUTH_LDAP_SERVER_URI")
AUTH_LDAP_USER_SEARCH_BASE = ENV.str("AUTH_LDAP_USER_SEARCH_BASE")
AUTH_LDAP_START_TLS = ENV.bool("AUTH_LDAP_START_TLS", default=True)
AUTH_LDAP_BIND_DN = ENV.str("AUTH_LDAP_BIND_DN", default="")
AUTH_LDAP_BIND_PASSWORD = ENV.str("AUTH_LDAP_BIND_PASSWORD", default="")
AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = ENV.bool("AUTH_LDAP_BIND_AS_AUTHENTICATING_USER", default=False)
AUTH_LDAP_MIRROR_GROUPS = ENV.bool("AUTH_LDAP_MIRROR_GROUPS", default=True)
AUTH_LDAP_GROUP_SEARCH_BASE = ENV.str("AUTH_LDAP_GROUP_SEARCH_BASE")

if AUTH_COLDFRONT_LDAP_SEARCH_SCOPE == "SUBTREE":
    AUTH_LDAP_USER_SEARCH = LDAPSearch(AUTH_LDAP_USER_SEARCH_BASE, ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(AUTH_LDAP_GROUP_SEARCH_BASE, ldap.SCOPE_SUBTREE, "(objectClass=groupOfNames)")
else:
    AUTH_LDAP_USER_SEARCH = LDAPSearch(AUTH_LDAP_USER_SEARCH_BASE, ldap.SCOPE_ONELEVEL, "(uid=%(user)s)")
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(AUTH_LDAP_GROUP_SEARCH_BASE, ldap.SCOPE_ONELEVEL, "(objectClass=groupOfNames)")

AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
AUTH_LDAP_USER_ATTR_MAP = ENV.dict(
    "AUTH_LDAP_USER_ATTR_MAP",
    default={
        "username": "uid",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    },
)

AUTHENTICATION_BACKENDS += [
    "django_auth_ldap.backend.LDAPBackend",
]
