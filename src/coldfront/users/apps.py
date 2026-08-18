# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "coldfront.users"

    def ready(self):
        from coldfront.models.features import register_models

        # Register models
        register_models(*self.get_models())

        from . import (
            signals,  # noqa: F401
        )
