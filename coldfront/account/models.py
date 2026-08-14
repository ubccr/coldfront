# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.models import ChangeLoggedModel
from coldfront.users.models import Token

__all__ = ("ThirdPartyAccount", "UserToken")


class UserToken(Token):
    """
    Proxy model for users to manage their own API tokens.
    """

    _coldfront_private = True

    class Meta:
        proxy = True
        verbose_name = "token"

    def get_absolute_url(self):
        return reverse("account:usertoken", args=[self.pk])


class ThirdPartyAccount(ChangeLoggedModel):
    """
    A link between a ColdFront user and an external third-party account
    (e.g. an ORCID iD).

    The link is verified via an OAuth "link-only" flow: the user must be
    already authenticated in a ColdFront session, and the provider confirms
    ownership of ``account_id``. ``is_verified`` is only ever set True by a
    successful OAuth callback.

    No tokens are stored here: the public-only design uses the provider
    account_id (e.g. the ORCID iD) to read public data, avoiding token
    storage entirely.
    """

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="third_party_accounts",
        verbose_name=_("user"),
    )

    provider = models.CharField(
        verbose_name=_("provider"),
        max_length=50,
    )

    account_id = models.CharField(
        verbose_name=_("account ID"),
        max_length=255,
        help_text=_("The identifier of the account at the provider (e.g. an ORCID iD)."),
    )

    is_verified = models.BooleanField(
        verbose_name=_("verified"),
        default=False,
        help_text=_("Whether the account ownership was verified via OAuth."),
    )

    scopes = models.JSONField(
        verbose_name=_("scopes"),
        default=list,
        blank=True,
        help_text=_("Scopes granted during the OAuth flow."),
    )

    linked_at = models.DateTimeField(
        verbose_name=_("linked at"),
        auto_now_add=True,
        blank=True,
        null=True,
    )

    last_synced_at = models.DateTimeField(
        verbose_name=_("last synced"),
        blank=True,
        null=True,
        help_text=_("When the provider's data was last synchronized (unused in the link-only phase)."),
    )

    class Meta:
        ordering = ("provider",)
        verbose_name = _("third-party account")
        verbose_name_plural = _("third-party accounts")
        unique_together = (
            # An account_id is linked to at most one ColdFront account.
            ("provider", "account_id"),
            # A user has at most one link per provider.
            ("user", "provider"),
        )

    def __str__(self):
        return f"{self.provider}:{self.account_id}"
