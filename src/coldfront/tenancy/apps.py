# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = "coldfront.tenancy"

    def ready(self):
        from coldfront.models.features import register_models

        # Register models
        register_models(*self.get_models())
