# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import inspect

from django.utils.translation import gettext_lazy as _

from coldfront.registry import registry

from .navigation import PluginMenu, PluginMenuButton, PluginMenuItem
from .templates import PluginTemplateExtension

__all__ = (
    "register_menu",
    "register_menu_items",
    "register_template_extensions",
)


def register_template_extensions(class_list):
    """
    Register a list of PluginTemplateExtension classes
    """
    for template_extension in class_list:
        # Validation
        if not inspect.isclass(template_extension):
            raise TypeError(
                _("PluginTemplateExtension class {template_extension} was passed as an instance!").format(
                    template_extension=template_extension
                )
            )
        if not issubclass(template_extension, PluginTemplateExtension):
            raise TypeError(
                _("{template_extension} is not a subclass of coldfront.plugins.PluginTemplateExtension!").format(
                    template_extension=template_extension
                )
            )

        if template_extension.models:
            # Registration for specific models
            models = template_extension.models
        else:
            # Global registration (no specific models)
            models = [None]
        for model in models:
            registry["plugins"]["template_extensions"][model].append(template_extension)


def register_menu(menu):
    if not isinstance(menu, PluginMenu):
        raise TypeError(_("{item} must be an instance of coldfront.plugins.PluginMenuItem").format(item=menu))
    registry["plugins"]["menus"].append(menu)


def register_menu_items(section_name, class_list):
    """
    Register a list of PluginMenuItem instances for a given menu section (e.g. plugin name)
    """
    # Validation
    for menu_link in class_list:
        if not isinstance(menu_link, PluginMenuItem):
            raise TypeError(
                _("{menu_link} must be an instance of coldfront.plugins.PluginMenuItem").format(menu_link=menu_link)
            )
        for button in menu_link.buttons:
            if not isinstance(button, PluginMenuButton):
                raise TypeError(
                    _("{button} must be an instance of coldfront.plugins.PluginMenuButton").format(button=button)
                )

    registry["plugins"]["menu_items"][section_name] = class_list
