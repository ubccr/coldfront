# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from taggit.models import GenericTaggedItemBase, TagBase

from coldfront.core.choices import ColorChoices
from coldfront.models import ChangeLoggedModel
from coldfront.models.features import CloningMixin
from coldfront.models.fields import ColorField
from coldfront.users.querysets import RestrictedQuerySet


class Tag(CloningMixin, ChangeLoggedModel, TagBase):
    id = models.BigAutoField(
        primary_key=True,
    )
    color = ColorField(
        verbose_name=_("color"),
        default=ColorChoices.COLOR_GREY,
    )
    description = models.CharField(
        verbose_name=_("description"),
        max_length=200,
        blank=True,
    )
    object_types = models.ManyToManyField(
        to="contenttypes.ContentType",
        related_name="+",
        blank=True,
        help_text=_("The object type(s) to which this tag can be applied."),
    )
    weight = models.PositiveSmallIntegerField(
        verbose_name=_("weight"),
        default=1000,
    )

    clone_fields = (
        "color",
        "description",
        "object_types",
    )

    class Meta:
        ordering = ("weight", "name")
        verbose_name = _("tag")
        verbose_name_plural = _("tags")

    def get_absolute_url(self):
        return reverse("core:tag", args=[self.pk])

    def slugify(self, tag, i=None):
        # Allow Unicode in Tag slugs (avoids empty slugs for Tags with all-Unicode names)
        slug = slugify(tag, allow_unicode=True)
        if i is not None:
            slug += "_%d" % i
        return slug


class TaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(
        to=Tag,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )

    _coldfront_private = True
    objects = RestrictedQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
        verbose_name = _("tagged item")
        verbose_name_plural = _("tagged items")
