# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from coldfront.config.base import INSTALLED_APPS, MIDDLEWARE
from coldfront.config.env import ENV

INSTALLED_APPS += [
    "coldfront.plugins.maintenance_mode",
]

MAINTENANCE_EXCLUDED_TASK_IDS = ENV.list("MAINTENANCE_EXCLUDED_TASK_IDS", default=[])
MAINTENANCE_EXCLUDED_USERS = ENV.list("MAINTENANCE_EXCLUDED_USERS", default=[])
MAINTENANCE_TASK_LOG_DIR = ENV.str("MAINTENANCE_TASK_LOG_DIR", default="")
MAINTENANCE_ALLOCATION_IMPACT_PADDING = ENV.int("MAINTENANCE_ALLOCATION_IMPACT_PADDING", default=0)

MIDDLEWARE += [
    "coldfront.plugins.maintenance_mode.middleware.MaintenanceModeMiddleware",
]
