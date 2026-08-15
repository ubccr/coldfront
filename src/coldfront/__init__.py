# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys

__version__ = "2.0.0"
VERSION = __version__


def manage():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coldfront.config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
