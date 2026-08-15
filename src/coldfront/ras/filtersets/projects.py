# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.ras.models import Project, ProjectUser
from coldfront.tenancy.filtersets import TenancyFilterSet
from coldfront.users.models import Group, User
from coldfront.views.filtersets import OrganizationalModelFilterSet, PrimaryModelFilterSet


class ProjectFilterSet(OrganizationalModelFilterSet, TenancyFilterSet):
    group_id = django_filters.ModelChoiceFilter(
        queryset=Group.objects.all(),
        label=_("Group"),
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "owner",
            "group_id",
            "tenant_id",
            "tenant",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(owner__username__icontains=value) | Q(name__icontains=value) | Q(description__icontains=value)
        )


class ProjectUserFilterSet(PrimaryModelFilterSet):
    user_id = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        label=_("User"),
    )

    class Meta:
        model = ProjectUser
        fields = (
            "id",
            "project_id",
            "user_id",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(user__username__icontains=value)
            | Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
        )
