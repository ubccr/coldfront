# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from coldfront.core.choices import CustomLinkButtonClassChoices
from coldfront.core.models import CustomLink

register = template.Library()

LINK_BUTTON = '<a href="{}"{} class="btn btn-sm btn-{}">{}</a>\n'

GROUP_BUTTON = """
<div class="dropdown">
    <button
        class="btn btn-sm btn-{} dropdown-toggle"
        type="button"
        data-bs-toggle="dropdown"
        aria-expanded="false">
        {}
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        {}
    </ul>
</div>
"""

GROUP_LINK = '<li><a class="dropdown-item" href="{}"{}>{}</a></li>\n'


@register.simple_tag(takes_context=True)
def custom_links(context, obj):
    """
    Render all applicable custom links for the given object.
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
    template_code = ""
    group_names = {}

    for cl in custom_links:
        # Organize custom links by group
        if cl.group_name and cl.group_name in group_names:
            group_names[cl.group_name].append(cl)
        elif cl.group_name:
            group_names[cl.group_name] = [cl]

        # Add non-grouped links
        else:
            button_class = (
                "outline-secondary" if cl.button_class == CustomLinkButtonClassChoices.DEFAULT else cl.button_class
            )
            try:
                if rendered := cl.render(link_context):
                    template_code += LINK_BUTTON.format(
                        rendered["link"], rendered["link_target"], button_class, rendered["text"]
                    )
            except Exception as e:
                template_code += (
                    f'<a class="btn btn-sm btn-outline-secondary" disabled="disabled" title="{e}">'
                    f'<i class="mdi mdi-alert"></i> {cl.name}</a>\n'
                )

    # Add grouped links to template
    for group, links in group_names.items():
        links_rendered = []

        for cl in links:
            try:
                if rendered := cl.render(link_context):
                    links_rendered.append(
                        GROUP_LINK.format(rendered["link"], rendered["link_target"], rendered["text"])
                    )
            except Exception as e:
                links_rendered.append(
                    f'<li><a class="dropdown-item" disabled="disabled" title="{e}">'
                    f'<span class="text-muted"><i class="mdi mdi-alert"></i> {cl.name}</span></a></li>'
                )

        if links_rendered:
            template_code += GROUP_BUTTON.format(links[0].button_class, escape(group), "".join(links_rendered))

    return mark_safe(template_code)
