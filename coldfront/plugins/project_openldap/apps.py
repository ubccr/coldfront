# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin apps.py"""

import importlib

from django.apps import AppConfig


class ProjectOpenldapConfig(AppConfig):
    name = "coldfront.plugins.project_openldap"

    def ready(self):
        importlib.import_module("coldfront.plugins.project_openldap.signals")
