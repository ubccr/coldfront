# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    "coldfront.plugins.slurm",
]

SLURM_SACCTMGR_PATH = ENV.str("SLURM_SACCTMGR_PATH", default="/usr/bin/sacctmgr")
SLURM_NOOP = ENV.bool("SLURM_NOOP", False)
SLURM_IGNORE_USERS = ENV.list("SLURM_IGNORE_USERS", default=["root"])
SLURM_IGNORE_ACCOUNTS = ENV.list("SLURM_IGNORE_ACCOUNTS", default=[])
