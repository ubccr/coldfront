# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.validators import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.models import ChangeLoggedModel
from coldfront.models.features import CloningMixin
from coldfront.utils.querydict import dict_to_querydict

__all__ = ("SavedFilter",)


class SavedFilter(CloningMixin, ChangeLoggedModel):
    """
    A set of predefined keyword parameters that can be reused to filter for specific objects.
    """

    object_types = models.ManyToManyField(
        to=ObjectType,
        related_name="saved_filters",
        help_text=_("The object type(s) to which this filter applies."),
    )
    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name=_("slug"),
        max_length=100,
        unique=True,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )
    user = models.ForeignKey(
        to="users.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        default=100,
    )
    enabled = models.BooleanField(
        verbose_name=_("enabled"),
        default=True,
    )
    shared = models.BooleanField(
        verbose_name=_("shared"),
        default=True,
    )
    parameters = models.JSONField(
        verbose_name=_("parameters"),
    )

    clone_fields = (
        "object_types",
        "weight",
        "enabled",
        "parameters",
    )

    class Meta:
        ordering = ("weight", "name")
        indexes = (
            models.Index(fields=("weight", "name"), name="core_savedfilter_weight_name"),  # Default ordering
        )
        verbose_name = _("saved filter")
        verbose_name_plural = _("saved filters")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("core:savedfilter", args=[self.pk])

    def clean(self):
        super().clean()

        # Verify that `parameters` is a JSON object
        if type(self.parameters) is not dict:
            raise ValidationError(
                {"parameters": _("Filter parameters must be stored as a dictionary of keyword arguments.")}
            )

    @property
    def url_params(self):
        qd = dict_to_querydict(self.parameters)
        return qd.urlencode()
