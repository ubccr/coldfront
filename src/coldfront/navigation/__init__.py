# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Optional, Sequence

from django.urls import reverse_lazy

__all__ = (
    "get_model_item",
    "get_model_buttons",
    "Menu",
    "MenuGroup",
    "MenuItem",
    "MenuItemButton",
)


#
# Navigation menu data classes
#


@dataclass
class MenuItemButton:
    link: str
    title: str
    icon_class: str
    _url: Optional[str] = None
    permissions: Optional[Sequence[str]] = ()
    color: Optional[str] = None

    def __post_init__(self):
        if self.link:
            self._url = reverse_lazy(self.link)

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value


@dataclass
class MenuItem:
    link: str
    link_text: str
    _url: Optional[str] = None
    permissions: Optional[Sequence[str]] = ()
    auth_required: Optional[bool] = False
    staff_only: Optional[bool] = False
    buttons: Optional[Sequence[MenuItemButton]] = ()

    def __post_init__(self):
        if self.link:
            self._url = reverse_lazy(self.link)

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value


@dataclass
class MenuGroup:
    label: str
    items: Sequence[MenuItem]


@dataclass
class Menu:
    label: str
    icon_class: str
    groups: Sequence[MenuGroup]

    @property
    def name(self):
        return self.label.replace(" ", "_")


#
# Utility functions
#


def get_model_item(app_label, model_name, label, actions=("add",), staff_only=False):
    return MenuItem(
        link=f"{app_label}:{model_name}_list",
        link_text=label,
        staff_only=staff_only,
        permissions=[f"{app_label}.view_{model_name}"],
        buttons=get_model_buttons(app_label, model_name, actions),
    )


def get_model_buttons(app_label, model_name, actions=("add",)):
    buttons = []

    if "add" in actions:
        buttons.append(
            MenuItemButton(
                link=f"{app_label}:{model_name}_add",
                title="Add",
                icon_class="fa-solid fa-plus",
                permissions=[f"{app_label}.add_{model_name}"],
            )
        )
    if "bulk_import" in actions:
        buttons.append(
            MenuItemButton(
                link=f"{app_label}:{model_name}_bulk_import",
                title="Import",
                icon_class="fa-solid fa-upload",
                permissions=[f"{app_label}.add_{model_name}"],
            )
        )

    return buttons
