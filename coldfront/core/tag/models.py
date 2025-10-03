# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import List, Type

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)


class Tag(TimeStampedModel):
    parent_tag = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=128)
    allowed_models = models.ManyToManyField(ContentType, blank=True, help_text="Inherited by its children.")
    """overrides any parent tags"""
    html_classes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Overriden by children. Meant for applying colors to tags. Bootstrap color docs: https://getbootstrap.com/docs/4.6/utilities/colors/",
        verbose_name="HTML classes",
    )

    user_permissions = models.CharField(
        choices=[("none", "None"), ("view", "View"), ("edit", "Edit")],
        help_text="None: users cannot view, add, or remove this tag. View: users can only view this tag. Edit: users can view, add, or remove this tag.",
        max_length=32,
        default="none",
    )

    # automatic fields
    created = models.DateTimeField(auto_now_add=True, editable=False)
    history = HistoricalRecords()

    @staticmethod
    def get_tag_field_name(other_obj):
        # get manager for m2m relationship with tag
        # resilience for models who may not have named the field "tags"
        other_m2m_fields = other_obj._meta.many_to_many
        tag_field_name = None
        for field in other_m2m_fields:
            if field.related_model == Tag:
                tag_field_name = field.name
        if not tag_field_name:
            logger.warning(f"{other_obj.__class__.__name__} has no many to many relatinship with Tag.")
            raise FieldDoesNotExist(f"{other_obj.__class__.__name__} has no many to many relatinship with Tag.")
        return tag_field_name

    @staticmethod
    def get_tags_visible_to_user(tags, user: User) -> QuerySet["Tag"]:
        if user.is_superuser:
            return tags.all()
        return tags.filter(user_permissions__in=["view", "edit"])

    @staticmethod
    def get_allowed_tags_for(model: Type[models.Model]):
        content_type = ContentType.objects.get_for_model(model)
        allowed_tags = Tag.objects.filter(allowed_models__in=[content_type])
        allowed_pks = list(allowed_tags.values_list("pk", flat=True))
        for tag in allowed_tags:
            allowed_pks.extend(tag.get_child_pks())
        allowed_tags = Tag.objects.filter(pk__in=allowed_pks)
        return allowed_tags

    def get_children(self) -> QuerySet["Tag"]:
        child_pks = self.get_children_pks()
        children = Tag.objects.filter(pk__in=child_pks)
        return children

    def get_child_pks(self) -> List[int]:
        children = Tag.objects.filter(parent_tag=self)
        child_pks = list(children.values_list("pk", flat=True))
        for child in children:
            child_pks.extend(child.get_children_pks())
        return child_pks

    @property
    def get_html_classes(self):
        if self.html_classes:
            return self.html_classes
        if self.parent_tag:
            return self.parent_tag.get_html_classes
        return self.html_classes

    def __str__(self):
        if self.parent_tag:
            return f"{self.parent_tag.name}/{self.name}"
        return self.name
