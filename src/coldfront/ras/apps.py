# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig


class RASConfig(AppConfig):
    name = "coldfront.ras"
    verbose_name = "RAS"

    def ready(self):
        from coldfront.models.features import register_models

        register_models(*self.get_models())

        # Import signals so receivers can connect
        import coldfront.ras.signals  # noqa

        # Connect Project group FK change tracking signals
        coldfront.ras.signals._connect_project_group_signals()
