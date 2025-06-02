# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib.util

from django.core.exceptions import ImproperlyConfigured

from coldfront.config.env import ENV

if importlib.util.find_spec("ldap") is None:
    raise ImproperlyConfigured("Please install required ldap module")

# ----------------------------------------------------------------------------
#  This enables searching for users via LDAP
# ----------------------------------------------------------------------------

LDAP_USER_SEARCH_SERVER_URI = ENV.str("LDAP_USER_SEARCH_SERVER_URI")
LDAP_USER_SEARCH_BASE = ENV.str("LDAP_USER_SEARCH_BASE")
LDAP_USER_SEARCH_BIND_DN = ENV.str("LDAP_USER_SEARCH_BIND_DN", default=None)
LDAP_USER_SEARCH_BIND_PASSWORD = ENV.str("LDAP_USER_SEARCH_BIND_PASSWORD", default=None)
LDAP_USER_SEARCH_CONNECT_TIMEOUT = ENV.float("LDAP_USER_SEARCH_CONNECT_TIMEOUT", default=2.5)
LDAP_USER_SEARCH_USE_SSL = ENV.bool("LDAP_USER_SEARCH_USE_SSL", default=True)
LDAP_USER_SEARCH_USE_TLS = ENV.bool("LDAP_USER_SEARCH_USE_TLS", default=False)
LDAP_USER_SEARCH_PRIV_KEY_FILE = ENV.str("LDAP_USER_SEARCH_PRIV_KEY_FILE", default=None)
LDAP_USER_SEARCH_CERT_FILE = ENV.str("LDAP_USER_SEARCH_CERT_FILE", default=None)
LDAP_USER_SEARCH_CACERT_FILE = ENV.str("LDAP_USER_SEARCH_CACERT_FILE", default=None)
LDAP_USER_SEARCH_CERT_VALIDATE_MODE = ENV.str("LDAP_USER_SEARCH_CERT_VALIDATE_MODE", default=None)

ADDITIONAL_USER_SEARCH_CLASSES = ["coldfront.plugins.ldap_user_search.utils.LDAPUserSearch"]
