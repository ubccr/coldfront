# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    "coldfront.plugins.project_openldap",
]

# Connection URI and bind user
PROJECT_OPENLDAP_SERVER_URI = ENV.str("PROJECT_OPENLDAP_SERVER_URI", default="")
PROJECT_OPENLDAP_BIND_USER = ENV.str("PROJECT_OPENLDAP_BIND_USER", default="")
PROJECT_OPENLDAP_BIND_PASSWORD = ENV.str("PROJECT_OPENLDAP_BIND_PASSWORD", default="")
# Timeout and SSL settings
PROJECT_OPENLDAP_CONNECT_TIMEOUT = ENV.float("PROJECT_OPENLDAP_CONNECT_TIMEOUT", default=2.5)
PROJECT_OPENLDAP_USE_SSL = ENV.bool("PROJECT_OPENLDAP_USE_SSL", default=True)
PROJECT_OPENLDAP_USE_TLS = ENV.bool("PROJECT_OPENLDAP_USE_TLS", default=False)
PROJECT_OPENLDAP_PRIV_KEY_FILE = ENV.str("PROJECT_OPENLDAP_PRIV_KEY_FILE", default=None)
PROJECT_OPENLDAP_CERT_FILE = ENV.str("PROJECT_OPENLDAP_CERT_FILE", default=None)
PROJECT_OPENLDAP_CACERT_FILE = ENV.str("PROJECT_OPENLDAP_CACERT_FILE", default=None)
# OU, GID, Arhive and sync excludes
PROJECT_OPENLDAP_OU = ENV.str("PROJECT_OPENLDAP_OU", default="")  # where projects will be stored
PROJECT_OPENLDAP_GID_START = ENV.int(
    "PROJECT_OPENLDAP_GID_START"
)  # where project gid numbering will start, no default value provided here on purpose, site should define sensible value
PROJECT_OPENLDAP_REMOVE_PROJECT = ENV.bool(
    "PROJECT_OPENLDAP_REMOVE_PROJECT", default=True
)  # remove projects on archive
PROJECT_OPENLDAP_ARCHIVE_OU = ENV.str(
    "PROJECT_OPENLDAP_ARCHIVE_OU", default=""
)  # where projects will be stored for archive e.g. ou=archive_projects...
PROJECT_OPENLDAP_EXCLUDE_USERS = ENV.tuple(
    "PROJECT_OPENLDAP_EXCLUDE_USERS", default=("coldfront",)
)  # never try to add these users to OpenLDAP - used by syncer script
# OpenLDAP description field for project
PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH = ENV.int(
    "PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH", default=100
)  # control the length of project title component from CF which is inserted into the OpenLDAP description field for each OpenLDAP project and is potentially truncated down
