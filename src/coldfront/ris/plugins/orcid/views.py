# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import secrets

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.generic import View

from coldfront.account.models import ThirdPartyAccount

from .client import ORCIDClient, ORCIDError

PROVIDER = "orcid"
SESSION_STATE_KEY = "account_state_orcid"

__all__ = ("OrcidCallbackView", "OrcidLinkView", "OrcidUnlinkView")


def _callback_url(request):
    return request.build_absolute_uri(reverse("plugins:orcid:callback"))


def _redirect_to_accounts(request):
    return redirect(reverse("account:third_party_accounts"))


class OrcidLinkView(LoginRequiredMixin, View):
    """
    Starts the ORCID link-only OAuth flow. The user must already be
    authenticated in a ColdFront session; ORCID never authenticates them into
    ColdFront.
    """

    def get(self, request):
        if ThirdPartyAccount.objects.filter(user=request.user, provider=PROVIDER).exists():
            messages.error(request, "You have already linked an ORCID account.")
            return _redirect_to_accounts(request)

        client = ORCIDClient()
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        request.session[SESSION_STATE_KEY] = state
        request.session["account_nonce_orcid"] = nonce

        url = client.build_authorize_url(state, nonce, _callback_url(request))
        return redirect(url)


class OrcidCallbackView(LoginRequiredMixin, View):
    """
    Handles the redirect back from ORCID. Verifies the OAuth ``state``
    (CSRF/cross-user protection), exchanges the code for an identity, and
    stores the verified ORCID link. Never creates a ColdFront user and never
    calls ``auth_login``.
    """

    def get(self, request):
        # Verify the one-time state parameter tied to the initiating session.
        expected = request.session.pop(SESSION_STATE_KEY, None)
        actual = request.GET.get("state")
        if not expected or not actual or not constant_time_compare(expected, actual):
            messages.error(request, "ORCID link could not be verified.")
            return _redirect_to_accounts(request)

        code = request.GET.get("code")
        if not code:
            messages.error(request, "ORCID authorization was canceled or failed.")
            return _redirect_to_accounts(request)

        client = ORCIDClient()
        try:
            token = client.exchange_code(code, _callback_url(request))
            identity = client.fetch_identity(token["access_token"])
            orcid = client.extract_orcid_id(identity, token)
        except (KeyError, ORCIDError, ValueError):
            messages.error(request, "Could not link ORCID account.")
            return _redirect_to_accounts(request)

        # Global uniqueness: an ORCID iD maps to a single ColdFront account.
        if ThirdPartyAccount.objects.filter(provider=PROVIDER, account_id=orcid).exclude(user=request.user).exists():
            messages.error(request, "This ORCID iD is already linked to another ColdFront account.")
            return _redirect_to_accounts(request)

        account, created = ThirdPartyAccount.objects.get_or_create(
            user=request.user,
            provider=PROVIDER,
            defaults={"account_id": orcid, "is_verified": True, "linked_at": timezone.now()},
        )
        if not created:
            account.account_id = orcid
            account.is_verified = True
            account.save()

        messages.success(request, f"Linked ORCID account {orcid}.")
        return _redirect_to_accounts(request)


class OrcidUnlinkView(LoginRequiredMixin, View):
    """
    Severs the ORCID link (POST only). Imported snapshots are ColdFront data
    and are not deleted.
    """

    def post(self, request):
        ThirdPartyAccount.objects.filter(user=request.user, provider=PROVIDER).delete()
        messages.success(request, "Unlinked ORCID account.")
        return _redirect_to_accounts(request)
