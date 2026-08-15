# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django.utils.translation import gettext_lazy as _

from coldfront.forms import NestedGroupModelForm, PrimaryModelForm
from coldfront.forms.fields import DynamicModelChoiceField, SlugField
from coldfront.forms.layouts import Slug
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
        Fieldset(
            "Tenant Group",
            "parent",
            "name",
            Slug(),
            "description",
            "tags",
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
        Fieldset(
            "Tenant",
            "name",
            Slug(),
            "group",
            "description",
            "tags",
        ),
    )
