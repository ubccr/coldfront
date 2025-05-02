# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin apps.py"""

from django.apps import AppConfig


class AutoComputeAllocationConfig(AppConfig):
    name = "coldfront.plugins.auto_compute_allocation"

    def ready(self):
        import coldfront.plugins.auto_compute_allocation.signals