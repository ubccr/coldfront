# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import (
    GroupManager as DjangoGroupManager,
)
from django.contrib.auth.models import (
    Permission,
    PermissionsMixin,
)
from django.contrib.auth.models import (
    UserManager as DjangoUserManager,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.users.querysets import RestrictedQuerySet
from coldfront.users.signals import group_membership_changed

__all__ = ("User", "UserManager", "Group", "GroupManager")


class GroupManager(DjangoGroupManager.from_queryset(RestrictedQuerySet)):
    pass


class UserManager(DjangoUserManager.from_queryset(RestrictedQuerySet)):
    pass


class User(AbstractBaseUser, PermissionsMixin):
    """
    ColdFront User model
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(
        _("first name"),
        max_length=150,
        blank=True,
    )
    last_name = models.CharField(
        _("last name"),
        max_length=150,
        blank=True,
    )
    email = models.EmailField(
        _("email address"),
        blank=True,
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(
        _("date joined"),
        default=timezone.now,
    )
    groups = models.ManyToManyField(
        to="users.Group",
        verbose_name=_("groups"),
        blank=True,
        related_name="users",
        related_query_name="user",
    )

    object_permissions = models.ManyToManyField(
        to="users.ObjectPermission",
        blank=True,
        related_name="users",
    )
    roles = models.ManyToManyField(
        to="users.Role",
        blank=True,
        related_name="users",
    )

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ("username",)
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def get_absolute_url(self):
        return reverse("users:user", args=[self.pk])

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def __str__(self):
        if not self.get_full_name():
            return self.username

        return f"{self.username} ({self.get_full_name()})"


class Group(models.Model):
    """
    ColdFront Group model.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=150,
        unique=True,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )

    # Replicate legacy Django permissions support from stock Group model
    # to ensure authentication backend compatibility
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_("permissions"),
        blank=True,
        related_name="groups",
        related_query_name="group",
    )

    object_permissions = models.ManyToManyField(
        to="users.ObjectPermission",
        blank=True,
        related_name="groups",
    )
    roles = models.ManyToManyField(
        to="users.Role",
        blank=True,
        related_name="groups",
    )

    objects = GroupManager()

    class Meta:
        ordering = ("name",)
        verbose_name = _("group")
        verbose_name_plural = _("groups")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("users:group", args=[self.pk])

    def natural_key(self):
        return (self.name,)

    def add_member(self, user):
        """Add a user to this group.  Fires ``group_membership_changed``
        signal so external sync jobs (LDAP, FreeIPA) can react.
        """
        if user in self.users.all():
            return
        self.users.add(user)
        group_membership_changed.send(
            sender=self,
            action="added",
            user=user,
        )

    def remove_member(self, user):
        """Remove a user from this group.  Fires ``group_membership_changed``
        signal so external sync jobs (LDAP, FreeIPA) can react.
        """
        if user not in self.users.all():
            return
        self.users.remove(user)
        group_membership_changed.send(
            sender=self,
            action="removed",
            user=user,
        )
