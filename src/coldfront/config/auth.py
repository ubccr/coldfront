# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from coldfront.config.base import AUTHENTICATION_BACKENDS, DEBUG
from coldfront.config.env import ENV
from coldfront.utils.security import validate_peppers

# ------------------------------------------------------------------------------
# ColdFront default authentication settings
# ------------------------------------------------------------------------------

AUTH_USER_MODEL = "users.User"

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = ENV.str("LOGOUT_REDIRECT_URL", LOGIN_URL)
CSRF_TRUSTED_ORIGINS = ENV.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SESSION_COOKIE_AGE = ENV.int("SESSION_INACTIVITY_TIMEOUT", default=60 * 60)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SECURE = True

API_TOKEN_PEPPERS = ENV.dict("API_TOKEN_PEPPERS", default={})

# Validate API token peppers
if API_TOKEN_PEPPERS:
    validate_peppers(API_TOKEN_PEPPERS)
elif DEBUG:
    API_TOKEN_PEPPERS = {"1": get_random_secret_key()}
else:
    raise ImproperlyConfigured("Required setting API_TOKEN_PEPPERS is not defined.")

# ------------------------------------------------------------------------------
# The remote authentication backend to use
# ------------------------------------------------------------------------------
REMOTE_AUTH_BACKEND = ENV.str("REMOTE_AUTH_BACKEND", default="coldfront.auth.RemoteUserBackend")

# ------------------------------------------------------------------------------
# ColdFront RemoteUserBackend settings
# ------------------------------------------------------------------------------
REMOTE_AUTH_ENABLED = ENV.bool("REMOTE_AUTH_ENABLED", default=False)
REMOTE_AUTH_AUTO_CREATE_GROUPS = ENV.bool("REMOTE_AUTH_AUTO_CREATE_GROUPS", default=False)
REMOTE_AUTH_AUTO_CREATE_USER = ENV.bool("REMOTE_AUTH_AUTO_CREATE_USER", default=False)
REMOTE_AUTH_DEFAULT_GROUPS = ENV.list("REMOTE_AUTH_DEFAULT_GROUPS", default=[])
REMOTE_AUTH_DEFAULT_PERMISSIONS = ENV.dict("REMOTE_AUTH_DEFAULT_PERMISSIONS", default={})
REMOTE_AUTH_GROUP_HEADER = ENV.str("REMOTE_AUTH_GROUP_HEADER", default="HTTP_REMOTE_USER_GROUP")
REMOTE_AUTH_GROUP_SEPARATOR = ENV.str("REMOTE_AUTH_GROUP_SEPARATOR", default="|")
REMOTE_AUTH_GROUP_SYNC_ENABLED = ENV.bool("REMOTE_AUTH_GROUP_SYNC_ENABLED", default=False)
REMOTE_AUTH_HEADER = ENV.str("REMOTE_AUTH_HEADER", default="HTTP_REMOTE_USER")
REMOTE_AUTH_SUPERUSER_GROUPS = ENV.list("REMOTE_AUTH_SUPERUSER_GROUPS", default=[])
REMOTE_AUTH_SUPERUSERS = ENV.list("REMOTE_AUTH_SUPERUSERS", default=[])
REMOTE_AUTH_USER_EMAIL = ENV.str("REMOTE_AUTH_USER_EMAIL", default="HTTP_REMOTE_USER_EMAIL")
REMOTE_AUTH_USER_FIRST_NAME = ENV.str("REMOTE_AUTH_USER_FIRST_NAME", default="HTTP_REMOTE_USER_FIRST_NAME")
REMOTE_AUTH_USER_LAST_NAME = ENV.str("REMOTE_AUTH_USER_LAST_NAME", default="HTTP_REMOTE_USER_LAST_NAME")

# ------------------------------------------------------------------------------
# ColdFront LDAPBackend settings
# ------------------------------------------------------------------------------
LDAP_SEARCH_SCOPE = ENV.str("LDAP_SEARCH_SCOPE", default="onelevel")
LDAP_IGNORE_CERT_ERRORS = ENV.bool("LDAP_IGNORE_CERT_ERRORS", default=False)
LDAP_USER_SEARCH_BASE = ENV.str("LDAP_USER_SEARCH_BASE", default=None)
LDAP_USER_SEARCH_QUERY = ENV.str("LDAP_USER_SEARCH_QUERY", default="(uid=%(user)s)")
LDAP_GROUP_SEARCH_BASE = ENV.str("LDAP_GROUP_SEARCH_BASE", default=None)
LDAP_GROUP_SEARCH_QUERY = ENV.str("LDAP_GROUP_SEARCH_QUERY", default="(objectClass=groupOfNames)")
LDAP_GROUP_TYPE = ENV.str("LDAP_GROUP_TYPE", default=None)

# Expose AUTH_LDAP_* settings directly
# See: https://django-auth-ldap.readthedocs.io/en/stable/example.html
AUTH_LDAP_SERVER_URI = ENV.str("AUTH_LDAP_SERVER_URI", default=None)
AUTH_LDAP_USER_DN_TEMPLATE = ENV.str("AUTH_LDAP_USER_DN_TEMPLATE", default=None)
AUTH_LDAP_START_TLS = ENV.bool("AUTH_LDAP_START_TLS", default=False)
AUTH_LDAP_BIND_DN = ENV.str("AUTH_LDAP_BIND_DN", default=None)
AUTH_LDAP_BIND_PASSWORD = ENV.str("AUTH_LDAP_BIND_PASSWORD", default=None)
AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = ENV.bool("AUTH_LDAP_BIND_AS_AUTHENTICATING_USER", default=False)
AUTH_LDAP_REQUIRE_GROUP = ENV.str("AUTH_LDAP_REQUIRE_GROUP", default=None)
AUTH_LDAP_DENY_GROUP = ENV.str("AUTH_LDAP_DENY_GROUP", default=None)
AUTH_LDAP_MIRROR_GROUPS = ENV.bool("AUTH_LDAP_MIRROR_GROUPS", default=True)
AUTH_LDAP_USER_FLAGS_BY_GROUP = ENV.dict("AUTH_LDAP_USER_FLAGS_BY_GROUP", default={})
AUTH_LDAP_USER_ATTR_MAP = ENV.dict(
    "AUTH_LDAP_USER_ATTR_MAP",
    default={
        "username": "uid",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    },
)

if type(REMOTE_AUTH_BACKEND) not in (list, tuple):
    REMOTE_AUTH_BACKEND = [REMOTE_AUTH_BACKEND]

AUTHENTICATION_BACKENDS += [
    *REMOTE_AUTH_BACKEND,
    "coldfront.auth.backends.ObjectPermissionBackend",
]

# ------------------------------------------------------------------------------
# Django social auth (social-auth-app-django) settings
# ------------------------------------------------------------------------------
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "coldfront.auth.backends.social_auth.match_user_by_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "coldfront.auth.backends.social_auth.user_default_groups_handler",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "coldfront.auth.backends.social_auth.sync_user_groups",
)

SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_CLEAN_USERNAME_FUNCTION = "coldfront.users.utils.clean_username"
SOCIAL_AUTH_USER_MODEL = AUTH_USER_MODEL
SOCIAL_AUTH_BACKEND_ATTRS = ENV.dict("SOCIAL_AUTH_BACKEND_ATTRS", default={})
SOCIAL_AUTH_MIRROR_GROUPS = ENV.bool("SOCIAL_AUTH_MIRROR_GROUPS", default=True)
