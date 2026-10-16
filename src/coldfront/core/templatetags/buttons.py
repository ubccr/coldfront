# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template
from django.utils.safestring import mark_safe

__all__ = ("action_buttons",)

register = template.Library()


@register.simple_tag(takes_context=True)
def action_buttons(context, actions, obj, multi=False, **kwargs):
    if actions and not isinstance(actions, (list, tuple)):
        actions = [actions]

    # ``return_url`` is ObjectAction-internal (URL wiring): build_attrs reads it
    # from ``context["return_url"]``. Route it to the context instead of passing
    # it through to render() where it would leak onto the button as an HTML attr.
    if "return_url" in kwargs:
        context["return_url"] = kwargs.pop("return_url")

    buttons = [action.render(context, obj, **kwargs) for action in actions if action.multi == multi]
    return mark_safe("".join(buttons))
