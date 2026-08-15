# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import ColorChoices
from coldfront.models import NestedGroupModel, OrganizationalModel
from coldfront.models.features import AllocatableResourceMixin
from coldfront.models.fields import ColorField
from coldfront.ras.choices import ResourceStatusChoices

from . import Allocation


class ResourceType(OrganizationalModel):
    """
    ResourceType's help organize generic resources; for example: Software, Cluster, Storage, etc.
    """

    slug = models.SlugField(
        verbose_name=_("slug"),
        max_length=100,
        unique=True,
    )
    color = ColorField(
        verbose_name=_("color"),
        default=ColorChoices.COLOR_GREY,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("resource type")
        verbose_name_plural = _("resource types")


class Resource(AllocatableResourceMixin, NestedGroupModel):
    """
    Resource's are generic assets that can be allocated to users. Each Resource can be
    assigned a ResourceType and an optional parent resource to create
    hierachical relationships.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
    )
    resource_type = models.ForeignKey(
        to="ras.ResourceType",
        on_delete=models.PROTECT,
        related_name="resources",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="resources",
        blank=True,
        null=True,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        choices=ResourceStatusChoices,
        default=ResourceStatusChoices.STATUS_ACTIVE,
    )
    allocations = GenericRelation(
        Allocation,
        content_type_field="resource_object_type",
        object_id_field="resource_object_id",
    )

    clone_fields = (
        "resource_type",
        "description",
        "status",
        "parent",
        "schema",
        "locked",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("generic resource")
        verbose_name_plural = _("generic resources")
        constraints = (
            models.UniqueConstraint(
                Lower("name"),
                "parent",
                "tenant",
                name="%(app_label)s_%(class)s_unique_name_parent_tenant",
            ),
            models.UniqueConstraint(
                Lower("name"),
                "parent",
                name="%(app_label)s_%(class)s_unique_name_parent",
                condition=Q(tenant__isnull=True),
                violation_error_message=_("Resource name must be unique"),
            ),
            models.UniqueConstraint(
                fields=("name",),
                name="%(app_label)s_%(class)s_name",
                condition=Q(parent__isnull=True) & Q(tenant__isnull=True),
                violation_error_message=_("A top-level resource with this name already exists."),
            ),
            models.UniqueConstraint(fields=("parent", "slug"), name="%(app_label)s_%(class)s_parent_slug"),
            models.UniqueConstraint(
                fields=("slug",),
                name="%(app_label)s_%(class)s_slug",
                condition=Q(parent__isnull=True),
                violation_error_message=_("A top-level resource with this slug already exists."),
            ),
        )

    def __str__(self):
        if self.resource_type:
            return f"{self.resource_type}: {self.name}"
        return self.name

    def get_status_color(self):
        return ResourceStatusChoices.colors.get(self.status)

        return None
