# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import ColorChoices
from coldfront.core.models import ObjectType
from coldfront.forms import OrganizationalModelFilterSetForm, PrimaryModelFilterSetForm
from coldfront.forms.fields import (
    ContentTypeChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from coldfront.forms.layouts import Date
from coldfront.ras.choices import AllocationChangeRequestStatusChoices, AllocationStatusChoices, ResourceStatusChoices
from coldfront.ras.models import (
    Allocation,
    Project,
    ProjectUser,
    Resource,
    ResourceType,
)
from coldfront.ras.models.change_requests import AllocationChangeRequest
from coldfront.tenancy.forms import TenancyFilterSetForm
from coldfront.users.models import Group, User


class ResourceTypeFilterSetForm(OrganizationalModelFilterSetForm):
    model = ResourceType
    color = forms.MultipleChoiceField(
        choices=ColorChoices.CHOICES,
        required=False,
        label=_("Color"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            "Resource Type",
            "color",
            "tag",
        ),
    )


class ResourceFilterSetForm(TenancyFilterSetForm, PrimaryModelFilterSetForm):
    model = Resource
    resource_type_id = forms.ModelChoiceField(
        queryset=ResourceType.objects.all(),
        required=False,
        label=_("Resource Type"),
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=ResourceStatusChoices,
        required=False,
    )
    parent_id = DynamicModelMultipleChoiceField(
        queryset=Resource.objects.all(),
        required=False,
        label=_("Parent"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Resource"),
            "resource_type_id",
            "status",
            "parent_id",
            "tag",
        ),
        Fieldset(
            _("Tenant"),
            "tenant_group_id",
            "tenant_id",
        ),
    )


class ProjectFilterSetForm(TenancyFilterSetForm, OrganizationalModelFilterSetForm):
    model = Project
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Owner"),
        required=False,
    )
    group_id = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label=_("Group"),
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Project"),
            "owner",
            "group_id",
            "tag",
        ),
        Fieldset(
            _("Tenant"),
            "tenant_group_id",
            "tenant_id",
        ),
    )


class AllocationFilterSetForm(TenancyFilterSetForm, PrimaryModelFilterSetForm):
    model = Allocation

    project_id = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    resource_object_type_id = ContentTypeChoiceField(
        label=_("Resource Object"),
        queryset=ObjectType.objects.with_feature("allocatable_resource"),
        required=False,
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=AllocationStatusChoices,
        required=False,
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Owner"),
        required=False,
    )
    start_date = forms.DateField(
        required=False,
        label=_("Start date (on or after)"),
    )
    end_date = forms.DateField(
        required=False,
        label=_("End date (on or before)"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Allocation"),
            "project_id",
            "resource_object_type_id",
            "status",
            "owner",
            Date("start_date"),
            Date("end_date"),
            "tag",
        ),
        Fieldset(
            _("Tenant"),
            "tenant_group_id",
            "tenant_id",
        ),
    )


class AllocationChangeRequestFilterSetForm(PrimaryModelFilterSetForm):
    model = AllocationChangeRequest
    allocation_id = forms.ModelChoiceField(
        queryset=Allocation.objects.all(),
        required=False,
        label=_("Allocation"),
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=AllocationChangeRequestStatusChoices,
        required=False,
    )
    requested_by_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Requested by"),
        required=False,
    )

    fieldsets = (
        Fieldset(
            _("Change Request"),
            "allocation_id",
            "status",
            "requested_by_id",
        ),
    )


class ProjectUserFilterSetForm(PrimaryModelFilterSetForm):
    model = ProjectUser
    project_id = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("User"),
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("User"),
            "project_id",
            "user_id",
            "tag",
        ),
    )
