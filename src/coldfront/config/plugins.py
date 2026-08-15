# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import importlib
import importlib.util
import warnings

from django.core.exceptions import ImproperlyConfigured

import coldfront
from coldfront.config.base import INSTALLED_APPS, MIDDLEWARE
from coldfront.config.env import ENV
from coldfront.exceptions import IncompatiblePluginError
from coldfront.plugins import PluginConfig
from coldfront.registry import registry

PLUGINS = ENV.list("PLUGINS", default=[])
PLUGINS_CONFIG = ENV.dict("PLUGINS_CONFIG", default={})
PLUGINS_CATALOG_CONFIG = ENV.dict("PLUGINS_CATALOG_CONFIG", default={})


# Register any configured plugins
for plugin_name in PLUGINS:
    try:
        # Import the plugin module
        plugin = importlib.import_module(plugin_name)
    except ModuleNotFoundError as e:
        if getattr(e, "name") == plugin_name:
            raise ImproperlyConfigured(
                f"Unable to import plugin {plugin_name}: Module not found. Check that the plugin module has been "
                f"installed within the correct Python environment."
            )
        raise e

    try:
        # Load the PluginConfig
        plugin_config: PluginConfig = plugin.config
    except AttributeError:
        raise ImproperlyConfigured(
            f"Plugin {plugin_name} does not provide a 'config' variable. This should be defined in the plugin's "
            f"__init__.py file and point to the PluginConfig subclass."
        )

    # Validate version compatibility and user-provided configuration settings and assign defaults
    if plugin_name not in PLUGINS_CONFIG:
        PLUGINS_CONFIG[plugin_name] = {}
    try:
        plugin_config.validate(PLUGINS_CONFIG[plugin_name], coldfront.VERSION)
    except IncompatiblePluginError as e:
        warnings.warn(f"Unable to load plugin {plugin_name}: {e}")
        continue

    # Register the plugin as installed successfully
    registry["plugins"]["installed"].append(plugin_name)

    plugin_module = "{}.{}".format(plugin_config.__module__, plugin_config.__name__)  # type: ignore

    # Gather additional apps to load alongside this plugin
    django_apps = plugin_config.django_apps
    if plugin_name in django_apps:
        django_apps.pop(plugin_name)
    if plugin_module not in django_apps:
        django_apps.append(plugin_module)

    # Test if we can import all modules (or its parent, for PluginConfigs and AppConfigs)
    for app in django_apps:
        if "." in app:
            parts = app.split(".")
            spec = importlib.util.find_spec(".".join(parts[:-1]))
        else:
            spec = importlib.util.find_spec(app)
        if spec is None:
            raise ImproperlyConfigured(
                f"Failed to load django_apps specified by plugin {plugin_name}: {django_apps} "
                f"The module {app} cannot be imported. Check that the necessary package has been "
                f"installed within the correct Python environment."
            )

    INSTALLED_APPS.extend(django_apps)

    # Preserve uniqueness of the INSTALLED_APPS list, we keep the last occurrence
    sorted_apps = reversed(list(dict.fromkeys(reversed(INSTALLED_APPS))))
    INSTALLED_APPS = list(sorted_apps)

    # Add middleware
    plugin_middleware = plugin_config.middleware
    if plugin_middleware and type(plugin_middleware) in (list, tuple):
        MIDDLEWARE.extend(plugin_middleware)
