# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.lib.forms import NestedGroupModelFilterSetForm, PrimaryModelFilterSetForm
from coldfront.lib.forms.fields import DynamicModelMultipleChoiceField, TagFilterField
from coldfront.lib.forms.layout import FieldSet
from coldfront.tenancy.models import Tenant, TenantGroup


class TenantGroupFilterSetForm(NestedGroupModelFilterSetForm):
    model = TenantGroup
    parent_id = forms.ModelChoiceField(queryset=TenantGroup.objects.all(), required=False, label=_("Parent Group"))
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "parent_id",
            name=_("Tenant Group"),
        ),
    )


class TenantFilterSetForm(PrimaryModelFilterSetForm):
    model = Tenant
    group_id = forms.ModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_("Tenant Group"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet(
            "q",
            "tag",
        ),
        FieldSet(
            "group_id",
            name=_("Tenant"),
        ),
    )


class TenancyFilterSetForm(forms.Form):
    tenant_group_id = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        null_option="None",
        label=_("Tenant group"),
    )
    tenant_id = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        null_option="None",
        query_params={"group_id": "$tenant_group_id"},
        label=_("Tenant"),
    )
