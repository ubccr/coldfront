# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template
from django.urls.exceptions import NoReverseMatch
from django.utils.module_loading import import_string

from coldfront.registry import registry
from coldfront.views import get_action_url

register = template.Library()


@register.inclusion_tag("generic/tabs.html", takes_context=True)
def model_view_tabs(context, instance):
    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    user = context["request"].user
    tabs = []

    # Retrieve registered views for this model
    try:
        views = registry["views"][app_label][model_name]
    except KeyError:
        # No views have been registered for this model
        views = []

    # Compile a list of tabs to be displayed in the UI
    for config in views:
        view = import_string(config["view"]) if type(config["view"]) is str else config["view"]
        if tab := getattr(view, "tab", None):
            if tab.permission and not user.has_perm(tab.permission):
                continue

            if attrs := tab.render(instance):
                active_tab = context.get("tab")
                try:
                    url = get_action_url(instance, action=config["name"], kwargs={"pk": instance.pk})
                except NoReverseMatch:
                    # No URL has been registered for this view; skip
                    continue
                tabs.append(
                    {
                        "name": config["name"],
                        "url": url,
                        "label": attrs["label"],
                        "badge": attrs["badge"],
                        "weight": attrs["weight"],
                        "is_active": active_tab and active_tab == tab,
                    }
                )

    # Order tabs by weight
    tabs = sorted(tabs, key=lambda x: x["weight"])

    return {
        "tabs": tabs,
    }
