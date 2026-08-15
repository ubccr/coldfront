# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.plugins import PluginConfig


class CrossrefConfig(PluginConfig):
    name = "coldfront.ris.providers.crossref"
    verbose_name = "Crossref provider"
    version = "0.1"
    description = "Searches publications via the public Crossref API (API-only provider)."
    base_url = "crossref"
    min_version = "2.0"
    # API-only: no link flow. Required settings are empty so the plugin loads
    # even without PLUGINS_CONFIG (graceful degradation).
    required_settings = []
    default_settings = {
        "base_url": "https://api.crossref.org",
        "display_name": "Crossref",
    }

    def ready(self):
        super().ready()

        # Importing the client applies its ``register_research_work_provider``
        # decorator, registering it with the ris registry.
        from .client import CrossrefClient  # noqa: F401


config = CrossrefConfig
