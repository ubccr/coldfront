# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.core.choices import CommentKindChoices, JobStatusChoices
from coldfront.core.models import CommentEntry, CustomLink, Job
from coldfront.users.models import User
from coldfront.views.filters import ContentTypeFilter
from coldfront.views.filtersets import BaseFilterSet, ChangeLoggedModelFilterSet

from .choices import CustomFieldTypeChoices
from .models import (
    CustomField,
    CustomFieldChoiceSet,
    ObjectChange,
    ObjectType,
    SavedFilter,
    TableConfig,
    Tag,
    TaggedItem,
)


class SavedFilterFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(),
        field_name="object_types",
    )
    object_type = django_filters.CharFilter(
        field_name="object_types__name",
        lookup_expr="exact",
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("User (ID)"),
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("User (name)"),
    )
    usable = django_filters.BooleanFilter(
        method="_usable",
    )

    class Meta:
        model = SavedFilter
        fields = ("id", "name", "slug", "description", "enabled", "shared", "weight")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))

    def _usable(self, queryset, name, value):
        """
        Return only SavedFilters that are both enabled and are shared (or belong to the current user).
        """
        user = self.request.user if self.request else None
        if not user or user.is_anonymous:
            if value:
                return queryset.filter(enabled=True, shared=True)
            return queryset.filter(Q(enabled=False) | Q(shared=False))
        if value:
            return queryset.filter(enabled=True).filter(Q(shared=True) | Q(user=user))
        return queryset.filter(Q(enabled=False) | Q(Q(shared=False) & ~Q(user=user)))


class TableConfigFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(),
        distinct=False,
        field_name="object_type",
    )
    object_type = django_filters.CharFilter(
        field_name="object_type__name",
        lookup_expr="exact",
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("User (ID)"),
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("User (name)"),
    )
    usable = django_filters.BooleanFilter(
        method="_usable",
    )

    class Meta:
        model = TableConfig
        fields = ("id", "name", "description", "table", "enabled", "shared", "weight")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value) | Q(table__icontains=value))

    def _usable(self, queryset, name, value):
        """
        Return only TableConfigs that are both enabled and are shared (or belong to the current user).
        """
        user = self.request.user if self.request else None
        if not user or user.is_anonymous:
            if value:
                return queryset.filter(enabled=True, shared=True)
            return queryset.filter(Q(enabled=False) | Q(shared=False))
        if value:
            return queryset.filter(enabled=True).filter(Q(shared=True) | Q(user=user))
        return queryset.filter(Q(enabled=False) | Q(Q(shared=False) & ~Q(user=user)))


class TagFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    content_type = django_filters.CharFilter(method="_content_type")
    content_type_id = django_filters.NumberFilter(method="_content_type_id")
    for_object_type_id = django_filters.NumberFilter(method="_for_object_type")

    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "slug",
            "color",
            "weight",
            "description",
            "object_types",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value) | Q(description__icontains=value))

    def _content_type(self, queryset, name, values):
        ct_filter = Q()

        # Compile list of app_label & model pairings
        for value in values:
            try:
                app_label, model = value.lower().split(".")
                ct_filter |= Q(app_label=app_label, model=model)
            except ValueError:
                pass

        # Get ContentType instances
        content_types = ContentType.objects.filter(ct_filter)

        return queryset.filter(core_taggeditem_items__content_type__in=content_types).distinct()

    def _content_type_id(self, queryset, name, values):
        # Get ContentType instances
        content_types = ContentType.objects.filter(pk__in=values)

        return queryset.filter(core_taggeditem_items__content_type__in=content_types).distinct()

    def _for_object_type(self, queryset, name, values):
        return queryset.filter(Q(object_types__id__in=values) | Q(object_types__isnull=True))


class TaggedItemFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    object_type = ContentTypeFilter(field_name="content_type")
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ContentType.objects.all(), field_name="content_type_id"
    )
    tag_id = django_filters.ModelMultipleChoiceFilter(queryset=Tag.objects.all())
    tag = django_filters.ModelMultipleChoiceFilter(
        field_name="tag__slug",
        queryset=Tag.objects.all(),
        to_field_name="slug",
    )

    class Meta:
        model = TaggedItem
        fields = ("id", "object_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(tag__name__icontains=value) | Q(tag__slug__icontains=value) | Q(tag__description__icontains=value)
        )


class ObjectChangeFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    time = django_filters.DateTimeFromToRangeFilter()
    changed_object_type = ContentTypeFilter()
    changed_object_type_id = django_filters.ModelMultipleChoiceFilter(queryset=ContentType.objects.all())
    related_object_type = ContentTypeFilter()
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        label=_("User (ID)"),
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("User name"),
    )

    class Meta:
        model = ObjectChange
        fields = (
            "id",
            "user",
            "user_name",
            "request_id",
            "action",
            "changed_object_type_id",
            "changed_object_id",
            "related_object_type",
            "related_object_id",
            "object_repr",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(user_name__icontains=value) | Q(object_repr__icontains=value) | Q(message__icontains=value)
        )


class CustomFieldChoiceSetFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    choice = django_filters.CharFilter(method="filter_by_choice")

    class Meta:
        model = CustomFieldChoiceSet
        fields = (
            "id",
            "name",
            "description",
            "order_alphabetically",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))

    def filter_by_choice(self, queryset, name, value):
        return queryset.filter(choices__icontains=value)


class CustomFieldFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    type = django_filters.MultipleChoiceFilter(
        choices=CustomFieldTypeChoices,
        distinct=False,
    )
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(), field_name="object_types"
    )
    object_type = ContentTypeFilter(field_name="object_types")
    related_object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(), distinct=False, field_name="related_object_type"
    )
    related_object_type = ContentTypeFilter()
    choice_set_id = django_filters.ModelMultipleChoiceFilter(
        queryset=CustomFieldChoiceSet.objects.all(),
        distinct=False,
    )
    choice_set = django_filters.ModelMultipleChoiceFilter(
        field_name="choice_set__name", queryset=CustomFieldChoiceSet.objects.all(), distinct=False, to_field_name="name"
    )

    class Meta:
        model = CustomField
        fields = (
            "id",
            "name",
            "label",
            "group_name",
            "required",
            "unique",
            "search_weight",
            "filter_logic",
            "ui_visible",
            "ui_editable",
            "weight",
            "is_cloneable",
            "description",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(label__icontains=value)
            | Q(group_name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


class JobFilterSet(ChangeLoggedModelFilterSet):
    """FilterSet for the Job model."""

    status = django_filters.MultipleChoiceFilter(
        choices=JobStatusChoices,
        label=_("Status"),
    )

    class Meta:
        model = Job
        fields = (
            "id",
            "name",
            "status",
            "interval",
            "queue_name",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value))


class CustomLinkFilterSet(ChangeLoggedModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(),
        field_name="object_types",
    )
    object_type = ContentTypeFilter(
        field_name="object_types",
    )

    class Meta:
        model = CustomLink
        fields = (
            "id",
            "name",
            "enabled",
            "link_text",
            "link_url",
            "weight",
            "group_name",
            "new_window",
            "button_class",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(link_text__icontains=value)
            | Q(link_url__icontains=value)
            | Q(group_name__icontains=value)
        )


class CommentEntryFilterSet(ChangeLoggedModelFilterSet):
    created = django_filters.DateTimeFromToRangeFilter()
    assigned_object_type = ContentTypeFilter()
    assigned_object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ContentType.objects.all(),
        distinct=False,
    )
    created_by_id = django_filters.ModelMultipleChoiceFilter(
        queryset=User.objects.all(),
        distinct=False,
        label=_("User (ID)"),
    )
    created_by = django_filters.ModelMultipleChoiceFilter(
        field_name="created_by__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("User (name)"),
    )
    kind = django_filters.MultipleChoiceFilter(
        choices=CommentKindChoices,
        distinct=False,
    )

    class Meta:
        model = CommentEntry
        fields = ("id", "assigned_object_type_id", "assigned_object_id", "created", "kind")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        q = Q(comments__icontains=value)
        return queryset.filter(q)
