# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import environ

ENV = environ.Env()
PROJECT_ROOT = environ.Path(__file__) - 3

# Default paths to environment files
env_paths = [
    environ.Path(Path.cwd(), ".env"),
    environ.Path("/etc/coldfront/coldfront.env"),
]

if ENV.str("COLDFRONT_ENV", default="") != "":
    env_paths = [environ.Path(ENV.str("COLDFRONT_ENV"))]

# Read in any environment files
for e in env_paths:
    try:
        with e.file(""):
            ENV.read_env(e())
    except FileNotFoundError:
        pass
