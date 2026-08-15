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

    buttons = [action.render(context, obj, **kwargs) for action in actions if action.multi == multi]
    return mark_safe("".join(buttons))
