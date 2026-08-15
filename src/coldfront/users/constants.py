# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import string

from django.db.models import Q

OBJECTPERMISSION_OBJECT_TYPES = (Q(public=True) & ~Q(app_label="core", model="objecttype")) | Q(
    app_label="core", model__in=["taggeditem"]
)

CONSTRAINT_TOKEN_USER = "$user"

# Django's four default model permissions. These receive special handling
# (dedicated checkboxes, model properties) and should not be registered
# as custom model actions.
RESERVED_ACTIONS = ("view", "add", "change", "delete")

# API tokens
TOKEN_HEADER_PREFIX = "Bearer"
TOKEN_PREFIX = "cft_"
TOKEN_KEY_LENGTH = 12
TOKEN_DEFAULT_LENGTH = 40
TOKEN_CHARSET = string.ascii_letters + string.digits
