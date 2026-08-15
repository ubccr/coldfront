# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import environ
from split_settings.tools import include, optional

from coldfront.config.env import ENV, PROJECT_ROOT

# ColdFront split settings
coldfront_configs = [
    "base.py",
    "database.py",
    "auth.py",
    "logging.py",
    "core.py",
    "email.py",
    "slurm.py",
    "plugins.py",
]

# Local settings overrides
local_configs = [
    # Local settings relative to coldfront.config package
    "local_settings.py",
    # System wide settings for production deployments
    "/etc/coldfront/local_settings.py",
    # Local settings relative to coldfront project root
    PROJECT_ROOT("local_settings.py"),
]

if ENV.str("COLDFRONT_CONFIG", default="") != "":
    # Local settings from path specified via environment variable
    local_configs.append(environ.Path(ENV.str("COLDFRONT_CONFIG"))())

for lc in local_configs:
    coldfront_configs.append(optional(lc))

include(*coldfront_configs)
