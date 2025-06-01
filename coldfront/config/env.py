# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import environ

ENV = environ.Env()
PROJECT_ROOT = environ.Path(__file__) - 3

# Default paths to environment files
env_paths = [
    PROJECT_ROOT.path(".env"),
    environ.Path("/etc/coldfront/coldfront.env"),
]

if ENV.str("COLDFRONT_ENV", default="") != "":
    env_paths.insert(0, environ.Path(ENV.str("COLDFRONT_ENV")))

# Read in any environment files
for e in env_paths:
    try:
        e.file("")
        ENV.read_env(e())
    except FileNotFoundError:
        pass
