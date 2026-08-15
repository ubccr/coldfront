# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import jsonschema
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from jsonschema.exceptions import ValidationError as JSONValidationError

from coldfront.models import PrimaryModel
from coldfront.models.features import CommentingMixin
from coldfront.models.fields import AutoSlugField
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.utils.strings import title


class Allocation(CommentingMixin, PrimaryModel):
    """
    An Allocation provides users access to resources.
    """

    slug = AutoSlugField(
        verbose_name=_("slug"),
    )
    project = models.ForeignKey(
        to="ras.Project",
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    resource_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    resource_object_id = models.PositiveBigIntegerField()
    resource_object = GenericForeignKey(
        ct_field="resource_object_type",
        fk_field="resource_object_id",
    )
    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="owned_allocations",
        on_delete=models.PROTECT,
        null=False,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        choices=AllocationStatusChoices,
        default=AllocationStatusChoices.STATUS_REQUESTED,
    )
    start_date = models.DateTimeField(
        verbose_name=_("start date"),
        blank=True,
        null=True,
    )
    end_date = models.DateTimeField(
        verbose_name=_("end date"),
        blank=True,
        null=True,
    )
    justification = models.TextField(
        verbose_name=_("justification"),
        blank=True,
        null=True,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
        null=True,
    )

    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="allocations",
        blank=True,
        null=True,
    )
    attribute_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("attributes"),
    )

    clone_fields = (
        "description",
        "status",
    )

    prerequisite_models = ("ras.Project",)

    class Meta:
        ordering = ["start_date"]
        verbose_name = _("allocation")
        verbose_name_plural = _("allocations")
        indexes = (models.Index(fields=("resource_object_type", "resource_object_id")),)
        permissions = (
            ("request", _("Request allocation")),
            ("approve", _("Approve allocation")),
            ("deny", _("Deny allocation")),
            ("activate", _("Activate allocation")),
            ("expire", _("Expire allocation")),
            ("revoke", _("Revoke allocation")),
            ("renew", _("Renew allocation")),
        )

    def get_status_color(self):
        return AllocationStatusChoices.colors.get(self.status)

    def __str__(self):
        return self.slug

    @property
    def attributes(self):
        """
        Returns a human-friendly representation of the allocation attributes defined according to its resource.
        """
        if not self.attribute_data or not self.resource_object or not self.resource_object.schema:
            return {}

        attrs = {}
        for name, options in self.resource_object.schema.get("properties", {}).items():
            key = options.get("title", title(name))
            attrs[key] = self.attribute_data.get(name)
        return dict(sorted(attrs.items()))

    def clean(self):
        super().clean()

        # Validate any attributes against the assigned resource objects's schema
        if self.resource_object and self.resource_object.schema:
            try:
                jsonschema.validate(self.attribute_data, schema=self.resource_object.schema)
            except JSONValidationError as e:
                raise ValidationError(_("Invalid schema: {error}").format(error=e))
        else:
            self.attribute_data = None
