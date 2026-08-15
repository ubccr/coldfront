# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import datetime
import importlib
from dataclasses import dataclass, field

from django.conf import settings

from coldfront.plugins import PluginConfig
from coldfront.registry import registry


@dataclass
class PluginAuthor:
    """
    Identifying information for the author of a plugin.
    """

    name: str
    org_id: str = ""
    url: str = ""


@dataclass
class PluginVersion:
    """
    Details for a specific versioned release of a plugin.
    """

    date: datetime.datetime = None
    version: str = ""
    coldfront_min_version: str = ""
    coldfront_max_version: str = ""
    has_model: bool = False
    is_certified: bool = False
    is_feature: bool = False
    is_integration: bool = False


@dataclass
class Plugin:
    """
    The representation of a ColdFront plugin in the catalog API.
    """

    id: str = ""
    icon_url: str = ""
    status: str = ""
    title_short: str = ""
    title_long: str = ""
    tag_line: str = ""
    description_short: str = ""
    slug: str = ""
    author: PluginAuthor | None = None
    created_at: datetime.datetime = None
    updated_at: datetime.datetime = None
    license_type: str = ""
    homepage_url: str = ""
    package_name_pypi: str = ""
    config_name: str = ""
    is_certified: bool = False
    release_latest: PluginVersion = field(default_factory=PluginVersion)
    release_recent_history: list[PluginVersion] = field(default_factory=list)
    is_local: bool = False  # Indicates that the plugin is listed in settings.PLUGINS (i.e. installed)
    is_loaded: bool = False  # Indicates whether the plugin successfully loaded at launch
    installed_version: str = ""
    coldfront_min_version: str = ""
    coldfront_max_version: str = ""


def get_local_plugins(plugins=None):
    """
    Return a dictionary of all locally-installed plugins, mapped by name.
    """
    plugins = plugins or {}
    local_plugins = {}

    # Gather all locally-installed plugins
    for plugin_name in settings.PLUGINS:
        plugin = importlib.import_module(plugin_name)
        plugin_config: PluginConfig = plugin.config
        installed_version = plugin_config.version
        if plugin_config.release_track:
            installed_version = f"{installed_version}-{plugin_config.release_track}"

        if plugin_config.author:
            author = PluginAuthor(
                name=plugin_config.author,
            )
        else:
            author = None

        local_plugins[plugin_config.name] = Plugin(
            config_name=plugin_config.name,
            title_short=plugin_config.verbose_name,
            title_long=plugin_config.verbose_name,
            tag_line=plugin_config.description,
            description_short=plugin_config.description,
            is_local=True,
            is_loaded=plugin_name in registry["plugins"]["installed"],
            installed_version=installed_version,
            coldfront_min_version=plugin_config.min_version,
            coldfront_max_version=plugin_config.max_version,
            author=author,
        )

    # Update catalog entries for local plugins, or add them to the list if not listed
    for k, v in local_plugins.items():
        if k in plugins:
            plugins[k].is_local = v.is_local
            plugins[k].is_loaded = v.is_loaded
            plugins[k].installed_version = v.installed_version
        else:
            plugins[k] = v

    # Update plugin table config for hidden and static plugins
    hidden = settings.PLUGINS_CATALOG_CONFIG.get("hidden", [])
    static = settings.PLUGINS_CATALOG_CONFIG.get("static", [])
    for k, v in plugins.items():
        v.hidden = k in hidden
        v.static = k in static

    return plugins
