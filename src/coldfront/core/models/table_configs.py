# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.validators import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.models import ChangeLoggedModel
from coldfront.models.features import CloningMixin
from coldfront.tables.utils import get_table_for_model

__all__ = ("TableConfig",)


class TableConfig(CloningMixin, ChangeLoggedModel):
    """
    A saved configuration of columns and ordering which applies to a specific table.
    """

    object_type = models.ForeignKey(
        to=ObjectType,
        on_delete=models.CASCADE,
        related_name="table_configs",
        help_text=_("The table's object type"),
    )
    table = models.CharField(
        verbose_name=_("table"),
        max_length=100,
    )
    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        default=1000,
    )
    enabled = models.BooleanField(
        verbose_name=_("enabled"),
        default=True,
    )
    shared = models.BooleanField(
        verbose_name=_("shared"),
        default=True,
    )
    columns = models.JSONField(
        verbose_name=_("columns"),
        default=list,
        blank=True,
        null=True,
    )
    ordering = models.JSONField(
        verbose_name=_("ordering"),
        default=list,
        blank=True,
        null=True,
    )

    clone_fields = ("object_type", "table", "enabled", "shared", "columns", "ordering")

    class Meta:
        ordering = ("weight", "name")
        indexes = (
            models.Index(fields=("weight", "name")),  # Default ordering
        )
        verbose_name = _("table config")
        verbose_name_plural = _("table configs")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:tableconfig", args=[self.pk])

    @property
    def table_class(self):
        return get_table_for_model(self.object_type.model_class(), name=self.table)

    @property
    def ordering_items(self):
        """
        Return a list of two-tuples indicating the column(s) by which the table is to be ordered and a boolean for each
        column indicating whether its ordering is ascending.
        """
        items = []
        for col in self.ordering or []:
            if col.startswith("-"):
                ascending = False
                col = col[1:]
            else:
                ascending = True
            items.append((col, ascending))
        return items

    def clean(self):
        super().clean()

        # Skip table validation until the object type and table have been set
        if not self.object_type_id or not self.table:
            return

        # Validate table
        if self.table_class is None:
            raise ValidationError(
                {
                    "table": _("Unknown table: {name}").format(name=self.table),
                }
            )

        table = self.table_class([])

        # Validate ordering columns
        for name in self.ordering or []:
            if name.startswith("-"):
                name = name[1:]  # Strip leading hyphen
            if name not in table.columns:
                raise ValidationError(
                    {
                        "ordering": _("Unknown column: {name}").format(name=name),
                    }
                )

        # Validate selected columns
        for name in self.columns or []:
            if name not in table.columns:
                raise ValidationError(
                    {
                        "columns": _("Unknown column: {name}").format(name=name),
                    }
                )
