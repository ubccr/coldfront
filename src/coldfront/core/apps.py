# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "coldfront.core"

    def ready(self):
        from coldfront import context_processors  # noqa: F401
        from coldfront.models.features import register_models

        from . import (
            notifications,  # noqa: F401
            signals,  # noqa: F401
            tasks,  # noqa: F401
        )

        # Register models
        register_models(*self.get_models())
