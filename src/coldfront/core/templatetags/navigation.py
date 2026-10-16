# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template

from coldfront.navigation.menu import get_menus

__all__ = ("nav",)


register = template.Library()


@register.inclusion_tag("navigation/menu.html", takes_context=True)
def nav(context):
    """
    Render the sidebar navigation menu for the current user.

    Build the visible menu structure and, along the way, find the single most
    specific item URL the current page falls under — an exact match, or a detail
    page beneath a list URL (e.g. /ras/projects/1/ under /ras/projects/). Using
    the longest matching URL keeps exactly one item highlighted when several are
    prefixes. Each menu section is flagged `active` when it contains the active
    item so the template can default-open it (auto-expand current section).
    """
    user = context["request"].user
    current_path = context["request"].path

    menus = []
    best_match = ""
    for menu in get_menus():
        groups = []
        for group in menu.groups:
            items = []
            for item in group.items:
                if getattr(item, "auth_required", False) and not user.is_authenticated:
                    continue
                if not user.has_perms(item.permissions):
                    continue
                if item.staff_only and not user.is_superuser:
                    continue
                buttons = [button for button in item.buttons if user.has_perms(button.permissions)]
                item_url = str(item.url or "")
                if (
                    item_url
                    and item_url != "/"
                    and current_path.startswith(item_url)
                    and len(item_url) > len(best_match)
                ):
                    best_match = item_url
                items.append((item, buttons, item_url))
            if items:
                groups.append((group, items))
        if groups:
            menus.append((menu, groups))

    # Second pass: flag the active item (drives its highlight) and, when a section
    # contains it, mark the section active (drives its default-open state).
    nav_items = []
    for menu, groups in menus:
        active = False
        out_groups = []
        for group, items in groups:
            out_items = []
            for item, buttons, item_url in items:
                item_active = bool(best_match) and item_url == best_match
                active = active or item_active
                out_items.append((item, buttons, item_active))
            out_groups.append((group, out_items))
        nav_items.append((menu, out_groups, active))

    return {
        "nav_items": nav_items,
    }
