# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.lib.forms import NestedGroupModelForm, PrimaryModelForm
from coldfront.lib.forms.fields import DynamicModelChoiceField, SlugField
from coldfront.lib.forms.layout import FieldSet
from coldfront.tenancy.models import Tenant, TenantGroup

__all__ = ("TenantGroupForm", "TenantForm")


class TenantGroupForm(NestedGroupModelForm):
    parent = DynamicModelChoiceField(
        label=_("Parent"),
        queryset=TenantGroup.objects.all(),
        required=False,
    )

    class Meta:
        model = TenantGroup
        fields = [
            "parent",
            "name",
            "slug",
            "description",
            "tags",
        ]

    fieldsets = (
        FieldSet(
            "parent",
            "name",
            "slug",
            "description",
            name=_("Tenant Group"),
        ),
    )


class TenantForm(PrimaryModelForm):
    slug = SlugField()
    group = DynamicModelChoiceField(
        label=_("Group"),
        queryset=TenantGroup.objects.all(),
        required=False,
    )

    class Meta:
        model = Tenant
        fields = [
            "name",
            "slug",
            "group",
            "description",
            "tags",
        ]

    fieldsets = (
        FieldSet(
            "name",
            "slug",
            "group",
            "description",
            name=_("Tenant"),
        ),
    )
