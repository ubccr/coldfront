# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import collections
from importlib import import_module

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from packaging import version

from coldfront.exceptions import IncompatiblePluginError
from coldfront.registry import registry

from .registration import register_menu, register_menu_items, register_template_extensions
from .templates import PluginTemplateExtension

# Initialize plugin registry
registry["plugins"].update(
    {
        "installed": [],
        "menus": [],
        "menu_items": {},
        "template_extensions": collections.defaultdict(list),
    }
)

DEFAULT_RESOURCE_PATHS = {
    "menu": "navigation.menu",
    "menu_items": "navigation.menu_items",
    "template_extensions": "template_content.template_extensions",
}


class PluginConfig(AppConfig):
    """
    Subclass of Django's built-in AppConfig class, to be used for ColdFront plugins.
    """

    # Plugin metadata
    author = ""
    author_email = ""
    description = ""
    version = ""
    release_track = ""

    # Root URL path under /plugins. If not set, the plugin's label will be used.
    base_url = None

    # Minimum/maximum compatible versions of ColdFront
    min_version = None
    max_version = None

    # Default configuration parameters
    default_settings = {}

    # Mandatory configuration parameters
    required_settings = []

    # Middleware classes provided by the plugin
    middleware = []

    # Django apps to append to INSTALLED_APPS when plugin requires them.
    django_apps = []

    # Optional plugin resources
    menu = None
    menu_items = None
    template_extensions = None

    def _load_resource(self, name):
        # Import from the configured path, if defined.
        if path := getattr(self, name, None):
            return import_string(f"{self.__module__}.{path}")

        # Fall back to the resource's default path. Return None if the module has not been provided.
        default_path = f"{self.__module__}.{DEFAULT_RESOURCE_PATHS[name]}"
        default_module, resource_name = default_path.rsplit(".", 1)
        try:
            module = import_module(default_module)
            return getattr(module, resource_name, None)
        except ModuleNotFoundError:
            pass

    def ready(self):
        from coldfront.models.features import register_models

        # Register models
        register_models(*self.get_models())

        # Register template content (if defined)
        if template_extensions := self._load_resource("template_extensions"):
            register_template_extensions(template_extensions)

        # Register navigation menu and/or menu items (if defined)
        if menu := self._load_resource("menu"):
            register_menu(menu)
        if menu_items := self._load_resource("menu_items"):
            register_menu_items(self.verbose_name, menu_items)

    @classmethod
    def validate(cls, user_config, coldfront_version):

        # Enforce version constraints
        current_version = version.parse(coldfront_version)
        if cls.min_version is not None:
            min_version = version.parse(cls.min_version)
            if current_version < min_version:
                raise IncompatiblePluginError(
                    f"Plugin {cls.__module__} requires ColdFront minimum version {cls.min_version} (current: "
                    f"{coldfront_version})."
                )
        if cls.max_version is not None:
            max_version = version.parse(cls.max_version)
            if current_version > max_version:
                raise IncompatiblePluginError(
                    f"Plugin {cls.__module__} requires ColdFront maximum version {cls.max_version} (current: "
                    f"{coldfront_version})."
                )

        # Verify required configuration settings
        for setting in cls.required_settings:
            if setting not in user_config:
                raise ImproperlyConfigured(
                    f"Plugin {cls.__module__} requires '{setting}' to be present in the PLUGINS_CONFIG section of "
                    f"configuration.py."
                )

        # Apply default configuration values
        for setting, value in cls.default_settings.items():
            if setting not in user_config:
                user_config[setting] = value


__all__ = (
    "PluginTemplateExtension",
    "PluginConfig",
)
