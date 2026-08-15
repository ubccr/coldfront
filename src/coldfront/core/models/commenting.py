# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CommentKindChoices
from coldfront.models import ChangeLoggedModel
from coldfront.models.features import CustomFieldsMixin, TagsMixin
from coldfront.registry import registry


class CommentEntry(CustomFieldsMixin, TagsMixin, ChangeLoggedModel):
    """
    A historical remark concerning an object; collectively, these form an object's comments. The comments are used to
    preserve historical context around an object, and complements ColdFront's built-in change logging. For example, you
    might record a new comment when an allocation undergoes review, or when a resource is updated.
    """

    assigned_object_type = models.ForeignKey(
        to="contenttypes.ContentType",
        on_delete=models.CASCADE,
    )
    assigned_object_id = models.PositiveBigIntegerField()
    assigned_object = GenericForeignKey(
        ct_field="assigned_object_type",
        fk_field="assigned_object_id",
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    kind = models.CharField(
        verbose_name=_("kind"),
        max_length=30,
        choices=CommentKindChoices,
        default=CommentKindChoices.KIND_INFO,
    )
    comments = models.TextField(
        verbose_name=_("comments"),
    )

    class Meta:
        ordering = ("-created",)
        indexes = (
            models.Index(fields=("-created",)),
            models.Index(fields=("assigned_object_type", "assigned_object_id")),
        )
        verbose_name = _("comment entry")
        verbose_name_plural = _("comment entries")

    def __str__(self):
        created = timezone.localtime(self.created)
        return (
            f"{created.date().isoformat()} {created.time().isoformat(timespec='minutes')} ({self.get_kind_display()})"
        )

    def get_absolute_url(self):
        return reverse("core:commententry", args=[self.pk])

    def clean(self):
        super().clean()

        # Validate the assigned object type
        if not self._has_commenting_feature(self.assigned_object_type):
            raise ValidationError(
                _("Commenting is not supported for this object type ({type}).").format(type=self.assigned_object_type)
            )

    def _has_commenting_feature(self, ct):
        """Check if the content type's model supports commenting."""
        try:
            test_func = registry["model_features"]["commenting"]
        except KeyError:
            return False
        model = ct.model_class()
        if model is None:
            return False
        return test_func(model)

    def get_kind_color(self):
        return CommentKindChoices.colors.get(self.kind)
