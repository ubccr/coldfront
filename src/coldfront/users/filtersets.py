# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db import connection
from django.db.models import Q
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from coldfront.core.models import ObjectType
from coldfront.ras.models import Allocation, Project
from coldfront.users.models import Group, ObjectPermission, Role, Token, User
from coldfront.views.filters import ContentTypeFilter
from coldfront.views.filtersets import BaseFilterSet

__all__ = (
    "GroupFilterSet",
    "ObjectPermissionFilterSet",
    "UserFilterSet",
    "TokenFilterSet",
)


class GroupFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        field_name="user",
        queryset=User.objects.all(),
        label=_("User (ID)"),
    )
    permission_id = django_filters.ModelMultipleChoiceFilter(
        field_name="object_permissions",
        queryset=ObjectPermission.objects.all(),
        label=_("Permission (ID)"),
    )

    class Meta:
        model = Group
        fields = ("id", "name", "description")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class UserFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label=_("Group"),
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label=_("Group (name)"),
    )
    permission_id = django_filters.ModelMultipleChoiceFilter(
        field_name="object_permissions",
        queryset=ObjectPermission.objects.all(),
        label=_("Permission (ID)"),
    )
    project_id = django_filters.ModelMultipleChoiceFilter(
        field_name="projects__project_id",
        queryset=Project.objects.all(),
        label=_("Project"),
    )
    allocation_id = django_filters.ModelMultipleChoiceFilter(
        field_name="allocations__allocation_id",
        queryset=Allocation.objects.all(),
        label=_("Allocation"),
    )
    available_for_allocation = django_filters.CharFilter(method="get_for_allocation")

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "date_joined",
            "last_login",
            "is_active",
            "is_superuser",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(email__icontains=value)
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_for_allocation(self, queryset, name, value):
        """
        Filter users that are a project but not on an allocation.

        - value = <project_id>_<allocation_id>
        """
        ids = value.split("_")
        if len(ids) != 2:
            return queryset.none()

        try:
            return queryset.filter(Q(projects__project_id=int(ids[0])) & ~Q(allocations__allocation_id=int(ids[1])))
        except ValueError:
            return queryset.none()


class RoleFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    permission_id = django_filters.ModelMultipleChoiceFilter(
        field_name="object_permissions",
        queryset=ObjectPermission.objects.all(),
        label=_("Permission (ID)"),
    )

    class Meta:
        model = Role
        fields = ("id", "name", "description", "weight")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class ObjectPermissionFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    object_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ObjectType.objects.all(), field_name="object_types"
    )
    object_type = ContentTypeFilter(field_name="object_types")
    can_view = django_filters.BooleanFilter(method="_check_action")
    can_add = django_filters.BooleanFilter(method="_check_action")
    can_change = django_filters.BooleanFilter(method="_check_action")
    can_delete = django_filters.BooleanFilter(method="_check_action")
    user_id = django_filters.ModelMultipleChoiceFilter(
        field_name="users",
        queryset=User.objects.all(),
        label=_("User"),
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="users__username",
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("User (name)"),
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label=_("Group"),
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label=_("Group (name)"),
    )

    class Meta:
        model = ObjectPermission
        fields = ("id", "name", "enabled", "object_types", "description")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))

    def _check_action(self, queryset, name, value):
        action = name.split("_")[1]
        if connection.features.supports_json_field_contains:
            if value:
                return queryset.filter(actions__contains=[action])
            return queryset.exclude(actions__contains=[action])

        # ``actions`` is a JSON list and ``__contains`` is unsupported on some
        # backends (e.g. SQLite). Resolve the matching object pks in Python and
        # filter the queryset by them so pagination/ordering still apply.
        matching_pks = [
            pk for pk, actions in queryset.values_list("pk", "actions") if value == (action in (actions or []))
        ]
        return queryset.filter(pk__in=matching_pks)


class TokenFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label=_("Search"),
    )
    user_id = django_filters.ModelMultipleChoiceFilter(
        field_name="user",
        queryset=User.objects.all(),
        distinct=False,
        label=_("User"),
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=User.objects.all(),
        distinct=False,
        to_field_name="username",
        label=_("User (name)"),
    )
    created = django_filters.DateTimeFilter()
    created__gte = django_filters.DateTimeFilter(field_name="created", lookup_expr="gte")
    created__lte = django_filters.DateTimeFilter(field_name="created", lookup_expr="lte")
    expires = django_filters.DateTimeFilter()
    expires__gte = django_filters.DateTimeFilter(field_name="expires", lookup_expr="gte")
    expires__lte = django_filters.DateTimeFilter(field_name="expires", lookup_expr="lte")
    last_used = django_filters.DateTimeFilter()
    last_used__gte = django_filters.DateTimeFilter(field_name="last_used", lookup_expr="gte")
    last_used__lte = django_filters.DateTimeFilter(field_name="last_used", lookup_expr="lte")

    class Meta:
        model = Token
        fields = (
            "id",
            "key",
            "pepper_id",
            "enabled",
            "write_enabled",
            "description",
            "created",
            "expires",
            "last_used",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(key=value) | Q(user__username__icontains=value) | Q(description__icontains=value))
