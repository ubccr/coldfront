# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from django.utils.autoreload import autoreload_started
from django.utils.translation import gettext_lazy as _


class StorageConfig(AppConfig):
    name = "coldfront.storage"
    label = "storage"
    verbose_name = _("Storage")

    def ready(self):
        from coldfront.lib.models.features import register_models
        from coldfront.storage.backends.dummy import seed_dummy_backends
        from coldfront.storage.backends.registry import register_backend

        from . import (
            billing,  # noqa: F401
            jobs,  # noqa: F401
            listeners,  # noqa: F401
            signals,  # noqa: F401
            views,  # noqa: F401
        )

        register_models(*self.get_models())

        # Register Dummy backend
        register_backend("coldfront.storage.backends.dummy.DummyBackend")

        # Seed storage dummy backends when starting dev server
        autoreload_started.connect(seed_dummy_backends)
