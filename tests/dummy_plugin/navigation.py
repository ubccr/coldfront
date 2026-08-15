# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext as _

from coldfront.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

items = (
    PluginMenuItem(
        link="plugins:dummy_plugin:dummy_model_list",
        link_text="Item 1",
        buttons=(
            PluginMenuButton(
                link="plugins:dummy_plugin:dummy_model_add",
                title="Button 1",
                icon_class="fa-solid fa-plus",
            ),
            PluginMenuButton(
                link="plugins:dummy_plugin:dummy_model_add",
                title="Button 2",
                icon_class="fa-solid fa-plus",
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
