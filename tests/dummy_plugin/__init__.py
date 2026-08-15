# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.plugins import PluginConfig


class DummyPluginConfig(PluginConfig):
    name = "tests.dummy_plugin"
    verbose_name = "Dummy plugin"
    version = "0.0"
    description = "For testing purposes only"
    base_url = "dummy-plugin"
    min_version = "2.0"
    max_version = "9.0"
    middleware = ["tests.dummy_plugin.middleware.DummyMiddleware"]

    def ready(self):
        super().ready()
        from . import tables  # noqa: F401


config = DummyPluginConfig
