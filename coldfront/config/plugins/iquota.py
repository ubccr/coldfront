# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    "coldfront.plugins.iquota",
]

IQUOTA_KEYTAB = ENV.str("IQUOTA_KEYTAB")
IQUOTA_CA_CERT = ENV.str("IQUOTA_CA_CERT")
IQUOTA_API_HOST = ENV.str("IQUOTA_API_HOST")
IQUOTA_API_PORT = ENV.str("IQUOTA_API_PORT", default="8080")
