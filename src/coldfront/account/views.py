# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from generic_notifications.models import Notification as GenericNotification
from generic_notifications.preferences import get_notification_preferences, save_notification_preferences
from generic_notifications.registry import registry as notification_registry
from generic_notifications.utils import get_notifications, mark_notifications_as_read
from social_core.backends.utils import load_backends

from coldfront.account.models import UserToken
from coldfront.core.models import ObjectChange
from coldfront.core.tables import ObjectChangeTable
from coldfront.registry import get_thirdparty_accounts, register_model_view
from coldfront.users import forms
from coldfront.views import generic

from .filtersets import NotificationFilterSet
from .forms import PasswordChangeForm
from .tables import NotificationTable, UserTokenTable

#
# Login/logout


class ColdFrontLoginView(LoginView):
    """
    ColdFront custom LoginView
    """

    template_name = "auth/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["auth_backends"] = self.get_auth_backends()
        return context

    def gen_auth_data(self, name, url, params):
        return {
            "display_name": settings.SOCIAL_AUTH_BACKEND_ATTRS.get(name, name),
            "url": f"{url}?{urlencode(params)}",
        }

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        logger = logging.getLogger("coldfront.auth.login")
        auth_login(self.request, form.get_user())

        logger.info(f"User {self.request.user} successfully authenticated")
        messages.success(self.request, _("Logged in as {user}.").format(user=self.request.user))

        # Ensure the user has a UserConfig defined. (This should normally be handled by
        # create_userconfig() on user creation.)
        if not hasattr(self.request.user, "config"):
            from coldfront.users.models import UserConfig

            UserConfig(user=self.request.user, data=settings.DEFAULT_USER_PREFERENCES).save()

        return HttpResponseRedirect(self.get_success_url())

    def get_auth_backends(self):
        """
        Return a list of configured auth backends from SOCIAL_AUTH settings.
        """

        auth_backends = []
        saml_idps = getattr(settings, "SOCIAL_AUTH_SAML_ENABLED_IDPS", {}).keys()

        for name in load_backends(settings.AUTHENTICATION_BACKENDS).keys():
            url = reverse("social:begin", args=[name])
            params = {}
            if next := self.request.GET.get("next"):
                params["next"] = next
            if name.lower() == "saml" and saml_idps:
                for idp in saml_idps:
                    params["idp"] = idp
                    data = self.gen_auth_data(name, url, params)
                    data["display_name"] = f"{data['display_name']} ({idp})"
                    auth_backends.append(data)
            else:
                auth_backends.append(self.gen_auth_data(name, url, params))

        return auth_backends


class HtmxLogoutView(LogoutView):
    """
    LogoutView that uses htmx
    """

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger("coldfront.auth.logout")
        auth_logout(request)
        logger.info(f"User {request.user} has logged out")
        messages.info(request, _("You have logged out."))
        redirect_to = self.get_success_url()
        if redirect_to != request.get_full_path():
            response = HttpResponse(status=204)
            response["HX-Redirect"] = redirect_to
            return response
        return super().get(request, *args, **kwargs)


#
# User profiles
#


class ProfileView(LoginRequiredMixin, View):
    template_name = "account/profile.html"

    def get(self, request):

        # Compile changelog table
        changelog = ObjectChange.objects.valid_models().restrict(request.user, "view").filter(user=request.user)[:20]
        changelog_table = ObjectChangeTable(changelog)
        changelog_table.orderable = False
        changelog_table.configure(request)

        return render(
            request,
            self.template_name,
            {
                "changelog_table": changelog_table,
                "active_tab": "profile",
            },
        )


class ChangePasswordView(LoginRequiredMixin, View):
    template_name = "account/password.html"

    def get(self, request):
        # LDAP users cannot change their password here
        if getattr(request.user, "ldap_username", None):
            messages.warning(request, _("LDAP-authenticated user credentials cannot be changed within ColdFront."))
            return redirect("account:profile")

        form = PasswordChangeForm(user=request.user)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "password",
            },
        )

    def post(self, request):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, _("Your password has been changed successfully."))
            return redirect("account:profile")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "change_password",
            },
        )


class ThirdPartyAccountsView(LoginRequiredMixin, View):
    """
    Shared "Third-Party Accounts" page. Loops over the registered third-party
    account providers (see ``coldfront.registry``) and renders, for each
    provider, either a Link button or the linked account plus an Unlink button.
    """

    template_name = "account/third_party_accounts.html"

    def get(self, request):
        account_by_provider = {account.provider: account for account in request.user.third_party_accounts.all()}

        providers = []
        for provider in get_thirdparty_accounts():
            account = account_by_provider.get(provider["key"])
            providers.append({**provider, "linked": bool(account), "account": account})

        return render(
            request,
            self.template_name,
            {
                "providers": providers,
                "active_tab": "third-party",
            },
        )


#
# User views for token management
#


@register_model_view(UserToken, "list", path="", detail=False)
class UserTokenListView(generic.ObjectListView):
    template_name = "account/usertoken_list.html"
    table = UserTokenTable

    def get_queryset(self, request):
        return UserToken.objects.filter(user=request.user)

    def get_extra_context(self, request):
        return {
            "active_tab": "api-tokens",
        }


@register_model_view(UserToken)
class UserTokenView(generic.ObjectView):
    def get_queryset(self, request):
        return UserToken.objects.filter(user=request.user)


@register_model_view(UserToken, "add", detail=False)
@register_model_view(UserToken, "edit")
class UserTokenEditView(generic.ObjectEditView):
    form = forms.UserTokenForm
    default_return_url = "account:usertoken_list"

    def get_queryset(self, request):
        return UserToken.objects.filter(user=request.user)

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.user = request.user
        return obj


@register_model_view(UserToken, "delete")
class UserTokenDeleteView(generic.ObjectDeleteView):
    default_return_url = "account:usertoken_list"

    def get_queryset(self, request):
        return UserToken.objects.filter(user=request.user)


#
# Notification views
#


class NotificationListView(generic.ObjectListView):
    """
    List view for user notifications
    """

    table = NotificationTable
    filterset = NotificationFilterSet
    template_name = "account/notification_list.html"
    actions = ()

    def get_queryset(self, request):
        if request.user.is_authenticated:
            return get_notifications(user=request.user)
        return GenericNotification.objects.none()

    def has_permission(self):
        """
        Bypass ColdFront permission checking for notifications. Users always see only
        their own notifications via the get_queryset() filter.
        """
        return True

    def post(self, request):
        action = request.POST.get("action", "")
        notification_id = request.POST.get("notification_id", "")

        if action == "mark_read" and notification_id:
            try:
                notification = GenericNotification.objects.get(id=notification_id, recipient=request.user)
                notification.mark_as_read()
            except GenericNotification.DoesNotExist:
                pass
        elif action == "mark_all_read":
            mark_notifications_as_read(user=request.user)
        elif action == "delete" and notification_id:
            GenericNotification.objects.filter(id=notification_id, recipient=request.user).delete()
        elif action == "delete_all":
            GenericNotification.objects.filter(recipient=request.user).delete()

        archive = request.GET.get("archive", "false") == "true"
        redirect_url = reverse("account:notification_list")
        if archive:
            redirect_url += "?archive=true"
        return redirect(redirect_url)


class NotificationDetailView(LoginRequiredMixin, View):
    """
    Detail view for a single notification. Marks it as read on view.
    """

    template_name = "account/notification.html"

    def get(self, request, pk):
        try:
            notification = GenericNotification.objects.get(id=pk, recipient=request.user)
            notification.mark_as_read()
        except GenericNotification.DoesNotExist:
            messages.error(request, _("Notification not found."))
            return redirect("account:notification_list")

        return render(
            request,
            self.template_name,
            {
                "notification": notification,
            },
        )


class NotificationPreferencesView(LoginRequiredMixin, View):
    """
    View for managing notification preferences.
    """

    template_name = "account/notification_preferences.html"

    def get(self, request):
        settings_data = get_notification_preferences(request.user)
        channels = {ch.key: ch for ch in notification_registry.get_all_channels()}
        frequencies = {freq.key: freq for freq in notification_registry.get_all_frequencies()}

        return render(
            request,
            self.template_name,
            {
                "settings_data": settings_data,
                "channels": channels,
                "frequencies": frequencies,
                "active_tab": "notifications",
            },
        )

    def post(self, request):
        save_notification_preferences(request.user, request.POST)
        messages.success(request, _("Notification preferences saved successfully."))
        return redirect("account:notification_preferences")
