# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.users.querysets import RestrictedQuerySet

__all__ = ("Role",)


class Role(models.Model):
    """
    A named collection of ObjectPermissions that can be assigned to Users and Groups.
    Roles provide a higher-level abstraction for permission management, allowing
    administrators to define reusable permission profiles (e.g., "Reviewer",
    "Principal Investigator") and assign them to users/groups rather than
    managing individual ObjectPermission assignments.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        default=100,
        help_text=_("Weight is used for ordering and precedence resolution."),
    )
    object_permissions = models.ManyToManyField(
        to="users.ObjectPermission",
        blank=True,
        related_name="roles",
    )

    clone_fields = (
        "description",
        "weight",
        "object_permissions",
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        ordering = ("weight", "name")
        verbose_name = _("role")
        verbose_name_plural = _("roles")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("users:role", args=[self.pk])
