# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.plugins import PluginConfig


class OrcidConfig(PluginConfig):
    name = "coldfront.ris.providers.orcid"
    verbose_name = "ORCID provider"
    version = "0.1"
    description = "Links ORCID accounts to ColdFront via a link-only OAuth flow."
    base_url = "orcid"
    min_version = "2.0"
    # Required settings are intentionally empty: the plugin must load even when
    # PLUGINS_CONFIG has not been populated, so that a site with no provider
    # configured degrades gracefully. Missing client credentials are surfaced
    # as a runtime error by the client when a link is actually attempted.
    required_settings = []
    default_settings = {
        "base_url": "https://orcid.org",
        "scope": "/authenticate",
    }

    def ready(self):
        super().ready()

        # Register the ORCID third-party account link flow with the account app.
        from coldfront.registry import register_thirdparty_account

        register_thirdparty_account(
            "orcid",
            display_name="ORCID",
            link_url="plugins:orcid:link",
            callback_url="plugins:orcid:callback",
            unlink_url="plugins:orcid:unlink",
        )

        # Importing the client applies its ``register_research_work_provider``
        # decorator, registering ORCID with the ris registry for Publication and
        # Funding.
        from .client import ORCIDClient  # noqa: F401


config = OrcidConfig
