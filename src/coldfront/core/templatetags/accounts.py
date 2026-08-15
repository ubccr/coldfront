# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template

from coldfront.registry import get_thirdparty_accounts as get_registered_thirdparty_accounts

register = template.Library()


@register.simple_tag
def get_thirdparty_accounts():
    """
    Return the list of registered third-party account providers. Used by the
    account navigation to conditionally render the \"Third-Party Accounts\" tab
    only when at least one provider is registered.
    """
    return get_registered_thirdparty_accounts()
