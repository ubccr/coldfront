# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StorageConfig(AppConfig):
    name = "coldfront.storage"
    label = "storage"
    verbose_name = _("Storage")

    def ready(self):
        from coldfront.models.features import register_models

        register_models(*self.get_models())

        # Auto-discover StorageBackend subclasses in the backends package
        from coldfront.storage.backends.registry import discover_backends

        discover_backends()

        from . import (
            listeners,  # noqa: F401
            signals,  # noqa: F401
            views,  # noqa: F401
        )
