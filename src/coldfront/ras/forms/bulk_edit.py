# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    AllocatableResourceBulkEditForm,
    OrganizationalModelBulkEditForm,
    PrimaryModelBulkEditForm,
)
from coldfront.forms.fields import ColorChoiceField
from coldfront.forms.layout import FieldSet
from coldfront.ras.choices import AllocationStatusChoices, ResourceStatusChoices
from coldfront.ras.models import Allocation, Project, ProjectUser, Resource, ResourceType
from coldfront.users.models import Group, User
from coldfront.utils.forms import add_blank_choice

#
# Resource Types
#


class ResourceTypeBulkEditForm(OrganizationalModelBulkEditForm):
    color = ColorChoiceField(
        required=False,
        label=_("Color"),
    )

    model = ResourceType
    nullable_fields = (
        "description",
        "color",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "color",
                name=_("Resource Type"),
            ),
        ]


#
# Resources
#


class ResourceBulkEditForm(AllocatableResourceBulkEditForm, PrimaryModelBulkEditForm):
    resource_type = forms.ModelChoiceField(
        queryset=ResourceType.objects.all(),
        required=False,
        label=_("Resource Type"),
    )
    status = forms.ChoiceField(
        choices=add_blank_choice(ResourceStatusChoices),
        required=False,
        label=_("Status"),
    )
    parent = forms.ModelChoiceField(
        queryset=Resource.objects.all(),
        required=False,
        label=_("Parent"),
    )

    model = Resource
    nullable_fields = (
        "tenant_group",
        "tenant",
        "description",
        "locked",
        "schema",
        "resource_type",
        "status",
        "parent",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "locked",
                "schema",
                name=_("Resource"),
            ),
            FieldSet(
                "resource_type",
                "status",
                "parent",
                name=_("Resource Type & Status"),
            ),
        ]


#
# Projects
#


class ProjectBulkEditForm(OrganizationalModelBulkEditForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Group"),
    )

    model = Project
    nullable_fields = (
        "tenant_group",
        "tenant",
        "description",
        "owner",
        "group",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "owner",
                "group",
                name=_("Project"),
            ),
        ]


#
# Project Users
#


class ProjectUserBulkEditForm(PrimaryModelBulkEditForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )

    model = ProjectUser

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "project",
                name=_("Project User"),
            ),
        ]


#
# Allocations
#


class AllocationBulkEditForm(PrimaryModelBulkEditForm):
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owner"),
    )
    status = forms.ChoiceField(
        choices=add_blank_choice(AllocationStatusChoices),
        required=False,
        label=_("Status"),
    )
    start_date = forms.DateTimeField(
        required=False,
        label=_("Start Date"),
    )
    end_date = forms.DateTimeField(
        required=False,
        label=_("End Date"),
    )
    justification = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label=_("Justification"),
    )
    model = Allocation
    nullable_fields = (
        "tenant_group",
        "tenant",
        "description",
        "project",
        "owner",
        "status",
        "start_date",
        "end_date",
        "justification",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "project",
                "owner",
                "status",
                name=_("Allocation"),
            ),
            FieldSet(
                "start_date",
                "end_date",
                name=_("Dates"),
            ),
            FieldSet(
                "justification",
                name=_("Text"),
            ),
        ]
