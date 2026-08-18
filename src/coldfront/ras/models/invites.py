# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.models import ChangeLoggedModel
from coldfront.users.querysets import RestrictedQuerySet


class ProjectInviteQuerySet(RestrictedQuerySet):
    """
    QuerySet for ProjectInvite with computed-status helpers.

    Statuses are never stored: they are derived from ``created`` (inherited
    from ChangeLoggingMixin) plus ``settings.INVITE_CODE_EXPIRE_SECONDS`` and
    the nullable ``accepted_at`` field.
    """

    def pending(self):
        """Valid invites that have not yet been accepted (not expired)."""
        cutoff = timezone.now() - timedelta(seconds=settings.INVITE_CODE_EXPIRE_SECONDS)
        return self.filter(accepted_at__isnull=True, created__gt=cutoff)

    def expired(self):
        """Stale invites that have not been accepted."""
        cutoff = timezone.now() - timedelta(seconds=settings.INVITE_CODE_EXPIRE_SECONDS)
        return self.filter(accepted_at__isnull=True, created__lte=cutoff)

    def accepted(self):
        """Invites that have already been accepted."""
        return self.filter(accepted_at__isnull=False)


class ProjectInvite(ChangeLoggedModel):
    """
    A one-time-use invite to add a user to a project.

    The invite token is a high-entropy cryptographically random value; only its
    SHA-256 digest is stored (``code_hash``). The raw token is sent to the
    invited address and used to look up the invite when it is accepted.
    """

    project = models.ForeignKey(
        to="ras.Project",
        on_delete=models.PROTECT,
        related_name="invites",
    )

    email = models.EmailField(
        verbose_name=_("email address"),
    )

    code_hash = models.CharField(
        verbose_name=_("invite code"),
        max_length=64,
        unique=True,
        blank=True,
        help_text=_("SHA-256 digest of the one-time invite token. Auto-generated on creation."),
    )

    accepted_at = models.DateTimeField(
        verbose_name=_("accepted"),
        null=True,
        blank=True,
    )

    invited_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_invites",
        blank=True,
        null=True,
    )

    # The raw token, available only on a freshly-created instance so callers can
    # email it. Never persisted.
    _raw_token = None

    objects = ProjectInviteQuerySet.as_manager()

    class Meta:
        ordering = ["created"]
        verbose_name = _("project invite")
        verbose_name_plural = _("project invites")

    def __str__(self):
        return f"{self.email} -> {self.project.name}"

    def get_absolute_url(self):
        return reverse("ras:projectinvite", args=[self.pk])

    @staticmethod
    def hash_code(code):
        """Return the SHA-256 digest of a raw invite token."""
        return hashlib.sha256(code.encode()).hexdigest()

    def generate_code(self):
        """Generate a fresh high-entropy token and store its SHA-256 digest."""
        token = secrets.token_urlsafe(32)
        self._raw_token = token
        self.code_hash = self.hash_code(token)

    def save(self, *args, **kwargs):
        if not self.code_hash:
            self.generate_code()
        super().save(*args, **kwargs)

    def get_raw_token(self):
        """Return the raw token for a freshly-created invite (used to email it)."""
        return self._raw_token

    @property
    def is_expired(self):
        """Invites are expired once ``created + INVITE_CODE_EXPIRE_SECONDS`` has passed."""
        return self.created + timedelta(seconds=settings.INVITE_CODE_EXPIRE_SECONDS) <= timezone.now()

    def get_status(self):
        """Computed display-only status: pending / expired / accepted."""
        if self.accepted_at is not None:
            return "accepted"
        if self.is_expired:
            return "expired"
        return "pending"

    def expire_date(self):
        """Returns the date when this invitation expires"""
        return self.created + timedelta(seconds=settings.INVITE_CODE_EXPIRE_SECONDS)

    def accept(self, user):
        """
        Accept the invite: mark it accepted and add ``user`` to the project.

        Returns True if the invite was consumed, False if it was already
        accepted or has expired. Adding a user who is already a project member
        is a no-op, not an error.
        """
        from coldfront.ras.models import ProjectUser

        if self.accepted_at is not None or self.is_expired:
            return False

        self.accepted_at = timezone.now()
        self.save()

        ProjectUser.objects.get_or_create(project=self.project, user=user)
        if self.project.group:
            self.project.group.add_member(user)
        return True
