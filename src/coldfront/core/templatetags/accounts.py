# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import template
from django.urls import reverse

from coldfront.lib.registry import get_thirdparty_accounts as get_registered_thirdparty_accounts

register = template.Library()


@register.simple_tag
def get_thirdparty_accounts():
    """
    Return the list of registered third-party account providers. Used by the
    account navigation to conditionally render the \"Third-Party Accounts\" tab
    only when at least one provider is registered.
    """
    return get_registered_thirdparty_accounts()


@register.inclusion_tag("account/tabs.html", takes_context=True)
def account_tabs(context):
    """
    Render the account navigation tabs (Profile, Password, API Tokens,
    Third-Party Accounts, Notifications). The active tab is determined by
    comparing the current view's ``tab`` (a ``ViewTab`` instance) against each
    account view's ``ViewTab`` by object identity, mirroring ``model_view_tabs``.
    """
    from coldfront.account import views

    user = context["request"].user
    current = context.get("tab")

    # (view, url_name), in display order
    items = [
        (views.ProfileView, "account:profile"),
        (views.ChangePasswordView, "account:change_password"),
        (views.UserTokenListView, "account:usertoken_list"),
        (views.ThirdPartyAccountsView, "account:third_party_accounts"),
        (views.NotificationPreferencesView, "account:notification_preferences"),
    ]

    tabs = []
    for view, url_name in items:
        tab = view.tab
        if attrs := tab.render(user):
            tabs.append(
                {
                    "label": attrs["label"],
                    "url": reverse(url_name),
                    "is_active": current and current == tab,
                }
            )

    return {"tabs": tabs}
