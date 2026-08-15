# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from coldfront.models import ColdFrontModel, OrganizationalModel
from coldfront.models.fields import AutoSlugField


class Project(OrganizationalModel):
    """A project is a container for housing research summary information related to allocations"""

    slug = AutoSlugField(
        verbose_name=_("slug"),
    )

    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="projects",
        blank=True,
        null=True,
    )

    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="owned_projects",
        on_delete=models.PROTECT,
        null=False,
    )

    group = models.ForeignKey(
        to="users.Group",
        on_delete=models.SET_NULL,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name=_("group"),
        help_text=_(
            "The Group associated with this project. Users added to the project are automatically added to this group."
        ),
    )

    clone_fields = ("tenant", "group")

    class Meta:
        ordering = ["name"]
        verbose_name = _("project")
        verbose_name_plural = _("projects")


class ProjectUser(ColdFrontModel):
    """A user that is a member of a project"""

    project = models.ForeignKey(
        to="ras.Project",
        on_delete=models.CASCADE,
        related_name="users",
    )

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="projects",
        on_delete=models.PROTECT,
        null=False,
    )

    clone_fields = ("project",)

    prerequisite_models = ("ras.Project",)

    class Meta:
        ordering = ["id"]
        unique_together = ("user", "project")
        verbose_name = _("project user")
        verbose_name_plural = _("project users")

    def __str__(self):
        return self.user.username
