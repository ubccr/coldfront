# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    OrganizationalModelBulkEditForm,
    PrimaryModelBulkEditForm,
)
from coldfront.tenancy.models import Tenant, TenantGroup

#
# Tenant Groups
#


class TenantGroupBulkEditForm(OrganizationalModelBulkEditForm):
    model = TenantGroup
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Tenant Group"),
                "description",
            ),
        ]


#
# Tenants
#


class TenantBulkEditForm(PrimaryModelBulkEditForm):
    group = forms.ModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_("Group"),
    )

    model = Tenant
    nullable_fields = (
        "description",
        "group",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Tenant"),
                "description",
                "group",
            ),
        ]
