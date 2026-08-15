# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import hmac
import secrets
import zoneinfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.users.constants import TOKEN_CHARSET, TOKEN_DEFAULT_LENGTH, TOKEN_KEY_LENGTH, TOKEN_PREFIX
from coldfront.users.querysets import RestrictedQuerySet
from coldfront.users.utils import get_current_pepper

__all__ = ("Token",)


class Token(models.Model):
    """
    An API token used for user authentication. This extends the stock model to allow each user to have multiple tokens.
    It also supports setting an expiration time and toggling write ability.
    """

    _token = None

    user = models.ForeignKey(
        to="users.User",
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )
    created = models.DateTimeField(
        verbose_name=_("created"),
        auto_now_add=True,
    )
    expires = models.DateTimeField(
        verbose_name=_("expires"),
        blank=True,
        null=True,
    )
    last_used = models.DateTimeField(
        verbose_name=_("last used"),
        blank=True,
        null=True,
    )
    enabled = models.BooleanField(
        verbose_name=_("enabled"),
        default=True,
        help_text=_("Disable to temporarily revoke this token without deleting it."),
    )
    write_enabled = models.BooleanField(
        verbose_name=_("write enabled"),
        default=True,
        help_text=_("Permit create/update/delete operations using this token"),
    )
    key = models.CharField(
        verbose_name=_("key"),
        max_length=TOKEN_KEY_LENGTH,
        unique=True,
        validators=[MinLengthValidator(TOKEN_KEY_LENGTH)],
        help_text=_("v2 token identification key"),
    )
    pepper_id = models.PositiveSmallIntegerField(
        verbose_name=_("pepper ID"),
        blank=True,
        null=True,
        help_text=_("ID of the cryptographic pepper used to hash the token"),
    )
    hmac_digest = models.CharField(
        verbose_name=_("digest"),
        max_length=64,
        help_text=_("SHA256 hash of the token and pepper (v2 only)"),
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ("-created",)
        verbose_name = _("token")
        verbose_name_plural = _("tokens")

    def __init__(self, *args, token=None, **kwargs):
        super().__init__(*args, **kwargs)

        # This stores the initial plaintext value (if given) on the creation of a new Token. If not provided, a
        # random token value will be generated and assigned immediately prior to saving the Token instance.
        self.token = token

    def __str__(self):
        return self.key

    def get_absolute_url(self):
        return reverse("users:token", args=[self.pk])

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        if not self._state.adding:
            raise ValueError("Cannot assign a new plaintext value for an existing token.")
        self._token = value
        if value is not None:
            self.key = self.key or self.generate_key()
            self.update_digest()

    @property
    def is_expired(self):
        """
        Check whether the token has expired.
        """
        if self.expires is None or timezone.now() < self.expires:
            return False
        return True

    @property
    def is_active(self):
        """
        Check whether the token is active (enabled and not expired).
        """
        return self.enabled and not self.is_expired

    def get_auth_header_prefix(self):
        """
        Return the HTTP Authorization header prefix for this token.
        """
        return f"Bearer {TOKEN_PREFIX}{self.key}."

    def clean(self):
        super().clean()

        if not settings.API_TOKEN_PEPPERS:
            raise ValidationError(_("Unable to save tokens: API_TOKEN_PEPPERS is not defined."))

        if self._state.adding:
            if self.pepper_id is not None and str(self.pepper_id) not in settings.API_TOKEN_PEPPERS:
                raise ValidationError(
                    _("Invalid pepper ID: {id}. Check configured API_TOKEN_PEPPERS.").format(id=self.pepper_id)
                )

        # Prevent creating a token with a past expiration date
        # while allowing updates to existing tokens.
        if self.pk is None and self.is_expired:
            current_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
            now = timezone.now().astimezone(current_tz)
            current_time_str = f"{now.date().isoformat()} {now.time().isoformat(timespec='seconds')}"

            # Translators: {current_time} is the current server date and time in ISO format,
            # {timezone} is the configured server time zone (for example, "UTC" or "Europe/Berlin").
            message = _(
                "Expiration time must be in the future. Current server time is {current_time} ({timezone})."
            ).format(current_time=current_time_str, timezone=current_tz.key)

            raise ValidationError({"expires": message})

    def save(self, *args, **kwargs):
        # If creating a new Token and no token value has been specified, generate one
        if self._state.adding and self.token is None:
            self.token = self.generate()

        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        """
        Generate and return a random alphanumeric key
        """
        return cls.generate(length=TOKEN_KEY_LENGTH)

    @staticmethod
    def generate(length=TOKEN_DEFAULT_LENGTH):
        """
        Generate and return a random token value of the given length.
        """
        return "".join(secrets.choice(TOKEN_CHARSET) for _ in range(length))

    def update_digest(self):
        """
        Recalculate and save the HMAC digest using the currently defined pepper and token values.
        """
        self.pepper_id, pepper = get_current_pepper()
        self.hmac_digest = hmac.new(pepper.encode("utf-8"), self.token.encode("utf-8"), hashlib.sha256).hexdigest()

    def validate(self, token):
        """
        Validate the given plaintext against the token.

        Calculate an HMAC from the Token's pepper ID and the given plaintext value, and check whether the result
        matches the recorded digest.
        """

        token = token.removeprefix(TOKEN_PREFIX)
        try:
            pepper = settings.API_TOKEN_PEPPERS[str(self.pepper_id)]
        except KeyError:
            # Invalid pepper ID
            return False
        digest = hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest == self.hmac_digest
