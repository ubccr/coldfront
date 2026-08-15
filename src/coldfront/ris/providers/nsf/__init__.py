# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.plugins import PluginConfig


class NSFConfig(PluginConfig):
    name = "coldfront.ris.providers.nsf"
    verbose_name = "NSF Awards provider"
    version = "0.1"
    description = "Searches funding via the public NSF Awards API (API-only provider)."
    base_url = "nsf"
    min_version = "2.0"
    # API-only: no link flow. Required settings are empty so the plugin loads
    # even without PLUGINS_CONFIG (graceful degradation).
    required_settings = []
    default_settings = {
        "base_url": "https://api.nsf.gov/services/v1",
        "display_name": "NSF",
    }

    def ready(self):
        super().ready()

        # Importing the client applies its ``register_research_work_provider``
        # decorator, registering it with the ris registry.
        from .client import NSFClient  # noqa: F401


config = NSFConfig
