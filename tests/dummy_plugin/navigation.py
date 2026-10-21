# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext as _

from coldfront.lib.plugins.navigation import PluginMenu, PluginMenuItem, PluginMenuItemButton

items = (
    PluginMenuItem(
        link="plugins:dummy_plugin:dummy_model_list",
        link_text="Item 1",
        buttons=(
            PluginMenuItemButton(
                link="plugins:dummy_plugin:dummy_model_add",
                title="Button 1",
                icon="heroicon.plus",
                variant="primary",
            ),
            PluginMenuItemButton(
                link="plugins:dummy_plugin:dummy_model_add",
                title="Button 2",
                icon="heroicon.plus",
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:dummy_plugin:dummy_model_list",
        link_text="Item 2",
    ),
)

menu = PluginMenu(
    label=_("Dummy Plugin"),
    groups=(("Group 1", items),),
)
menu_items = items
