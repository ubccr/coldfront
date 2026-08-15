# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib import messages
from django.db.models import ProtectedError, RestrictedError
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from coldfront.plugins import PluginConfig


class ViewTab:
    """
    ViewTabs are used for navigation among multiple object-specific views, such as the changelog or journal for
    a particular object.

    Args:
        label: Human-friendly text
        visible: A callable which determines whether the tab should be displayed. This callable must accept exactly one
            argument: the object instance. If a callable is not specified, the tab's visibility will be determined by
            its badge (if any) and the value of `hide_if_empty`.
        badge: A static value or callable to display alongside the label (optional). If a callable is used, it must
            accept a single argument representing the object being viewed.
        weight: Numeric weight to influence ordering among other tabs (default: 1000)
        permission: The permission required to display the tab (optional).
        hide_if_empty: If true, the tab will be displayed only if its badge has a meaningful value. (This parameter is
            evaluated only if the tab is permitted to be displayed according to the `visible` parameter.)
    """

    def __init__(self, label, visible=None, badge=None, weight=1000, permission=None, hide_if_empty=False):
        self.label = label
        self.visible = visible
        self.badge = badge
        self.weight = weight
        self.permission = permission
        self.hide_if_empty = hide_if_empty

    def render(self, instance):
        """
        Return the attributes needed to render a tab in HTML if the tab should be displayed. Otherwise, return None.
        """
        if self.visible is not None and not self.visible(instance):
            return None
        badge_value = self._get_badge_value(instance)
        if self.badge and self.hide_if_empty and not badge_value:
            return None
        return {
            "label": self.label,
            "badge": badge_value,
            "weight": self.weight,
        }

    def _get_badge_value(self, instance):
        if not self.badge:
            return None
        if callable(self.badge):
            return self.badge(instance)
        return self.badge


def get_viewname(model, action=None, rest_api=False):
    """
    Return the view name for the given model and action, if valid.

    :param model: The model or instance to which the view applies
    :param action: A string indicating the desired action (if any); e.g. "add" or "list"
    :param rest_api: A boolean indicating whether this is a REST API view
    """
    is_plugin = isinstance(model._meta.app_config, PluginConfig)
    app_label = model._meta.app_label
    model_name = model._meta.model_name

    if rest_api:
        viewname = f"{app_label}-api:{model_name}"
        if is_plugin:
            viewname = f"plugins-api:{viewname}"
        if action:
            viewname = f"{viewname}-{action}"

    else:
        viewname = f"{app_label}:{model_name}"
        if is_plugin:
            viewname = f"plugins:{viewname}"
        if action:
            viewname = f"{viewname}_{action}"

    return viewname


def get_action_url(model, action=None, rest_api=False, kwargs=None):
    """
    Return the URL for the given model and action, if valid; otherwise raise NoReverseMatch.
    Will defer to _get_action_url() on the model if it exists.

    :param model: The model or instance to which the URL belongs
    :param action: A string indicating the desired action (if any); e.g. "add" or "list"
    :param rest_api: A boolean indicating whether this is a REST API action
    :param kwargs: A dictionary of keyword arguments for the view to include when resolving its URL path (optional)
    """
    if hasattr(model, "_get_action_url"):
        return model._get_action_url(action, rest_api, kwargs)

    return reverse(get_viewname(model, action, rest_api), kwargs=kwargs)


def handle_protectederror(obj_list, request, e):
    """
    Generate a user-friendly error message in response to a ProtectedError or RestrictedError exception.
    """
    if type(e) is ProtectedError:
        protected_objects = list(e.protected_objects)
    elif type(e) is RestrictedError:
        protected_objects = list(e.restricted_objects)
    else:
        raise e

    # Formulate the error message
    err_message = _("Unable to delete <strong>{objects}</strong>. {count} dependent objects were found: ").format(
        objects=", ".join(str(obj) for obj in obj_list),
        count=len(protected_objects) if len(protected_objects) <= 50 else _("More than 50"),
    )

    # Append dependent objects to error message
    dependent_objects = []
    for dependent in protected_objects[:50]:
        if hasattr(dependent, "get_absolute_url"):
            dependent_objects.append(f'<a href="{dependent.get_absolute_url()}">{escape(dependent)}</a>')
        else:
            dependent_objects.append(escape(str(dependent)))
    err_message += ", ".join(dependent_objects)

    messages.error(request, mark_safe(err_message))
