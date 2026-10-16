# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.translation import gettext as _

from coldfront.core.choices import ColorChoices
from coldfront.navigation import MenuGroup

__all__ = (
    "PluginMenu",
    "PluginMenuItem",
    "PluginMenuItemButton",
)


class PluginMenu:
    icon = "tablericon.puzzle"

    def __init__(self, label, groups, icon=None):
        self.label = label
        self.groups = [MenuGroup(label, items) for label, items in groups]
        if icon is not None:
            self.icon = icon

    @property
    def name(self):
        return slugify(self.label)


class PluginMenuItem:
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the van menu.

    Links are specified as Django reverse URL strings suitable for rendering via {% url item.link %}.
    Alternatively, a pre-generated url can be set on the object which will be rendered literally.
    Buttons are each specified as a list of PluginMenuItemButton instances.
    """

    _url = None

    def __init__(self, link, link_text, auth_required=False, staff_only=False, permissions=None, buttons=None):
        self.link = link
        self.link_text = link_text
        self.auth_required = auth_required
        self.staff_only = staff_only
        if link:
            self._url = reverse_lazy(link)
        if permissions is not None:
            if type(permissions) not in (list, tuple):
                raise TypeError(_("Permissions must be passed as a tuple or list."))
            self.permissions = permissions
        else:
            self.permissions = []
        if buttons is not None:
            if type(buttons) not in (list, tuple):
                raise TypeError(_("Buttons must be passed as a tuple or list."))
            self.buttons = buttons
        else:
            self.buttons = []

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value


class PluginMenuItemButton:
    """
    This class represents a button within a PluginMenuItem. The `icon` is a
    cotton-icons pack name (heroicon.* / tablericon.* / lucideicon.*). The
    `variant` is a daisyUI button variant: a ColorChoices color, or "ghost"
    (the default).
    """

    _url = None

    def __init__(self, link, title, icon, variant="ghost", permissions=None):
        self.link = link
        self.title = title
        self.icon = icon
        if variant != "ghost" and variant not in ColorChoices.values():
            raise ValueError(_("Button variant must be a ColorChoices color or 'ghost'."))
        self.variant = variant
        if link:
            self._url = reverse_lazy(link)
        if permissions is not None:
            if type(permissions) not in (list, tuple):
                raise TypeError(_("Permissions must be passed as a tuple or list."))
            self.permissions = permissions
        else:
            self.permissions = []

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
