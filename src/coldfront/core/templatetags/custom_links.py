# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template
from django.utils.safestring import mark_safe
from django_cotton import render_component

from coldfront.core.models import CustomLink

register = template.Library()


@register.simple_tag(takes_context=True)
def custom_links(context, obj):
    """
    Render all applicable custom links for the given object.

    Builds a plain data structure and delegates the markup to the
    `c-cf.button.custom_links` cotton component.
    """

    from coldfront.core.models import ObjectType

    object_type = ObjectType.objects.get_for_model(obj)
    custom_links = CustomLink.objects.filter(object_types=object_type, enabled=True)
    if not custom_links:
        return ""

    # Pass select context data when rendering the CustomLink
    link_context = {
        "object": obj,
        "debug": context.get("debug", False),
        "request": context["request"],
        "user": context["user"],
        "perms": context["perms"],
    }

    links = []  # non-grouped links
    groups = {}  # group name -> {name, variant, links[]}

    for cl in custom_links:
        item = {
            "variant": cl.button_variant,
            "new_window": cl.new_window,
            "name": cl.name,
        }
        try:
            rendered = cl.render(link_context)
            if not rendered:
                continue
            item["text"] = rendered["text"]
            item["link"] = rendered["link"]
        except Exception as e:
            item["disabled"] = True
            item["error"] = str(e)

        if cl.group_name:
            group = groups.setdefault(
                cl.group_name,
                {"name": cl.group_name, "variant": cl.button_variant, "links": []},
            )
            group["links"].append(item)
        else:
            links.append(item)

    return mark_safe(
        render_component(
            context["request"],
            "cf.button.custom_links",
            {"links": links, "groups": list(groups.values())},
        )
    )
