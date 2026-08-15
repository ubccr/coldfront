# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    NestedGroupModelImportForm,
    PrimaryModelImportForm,
)
from coldfront.forms.fields import CSVModelChoiceField, SlugField
from coldfront.tenancy.models import Tenant, TenantGroup


class TenantGroupImportForm(NestedGroupModelImportForm):
    parent = CSVModelChoiceField(
        label=_("Parent"),
        queryset=TenantGroup.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Parent group"),
    )

    class Meta:
        model = TenantGroup
        fields = (
            "name",
            "slug",
            "parent",
            "description",
            "tags",
        )


class TenantImportForm(PrimaryModelImportForm):
    slug = SlugField()
    group = CSVModelChoiceField(
        label=_("Group"),
        queryset=TenantGroup.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Assigned group"),
    )

    class Meta:
        model = Tenant
        fields = (
            "name",
            "slug",
            "group",
            "description",
            "tags",
        )
