# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.tables import NestedGroupModelTable, PrimaryModelTable, columns
from coldfront.tenancy.models import Tenant, TenantGroup


class TenantGroupTable(NestedGroupModelTable):
    tenant_count = columns.LinkedCountColumn(
        viewname="tenancy:tenant_list", url_params={"group_id": "pk"}, verbose_name=_("Tenants")
    )
    tags = columns.TagColumn(url_name="tenancy:tenantgroup_list")

    class Meta(NestedGroupModelTable.Meta):
        model = TenantGroup
        fields = (
            "pk",
            "id",
            "name",
            "parent",
            "tenant_count",
            "description",
            "slug",
            "tags",
            "created",
            "last_updated",
            "actions",
        )
        default_columns = ("pk", "name", "tenant_count", "description")


class TenantTable(PrimaryModelTable):
    name = tables.Column(verbose_name=_("Name"), linkify=True)
    group = tables.Column(verbose_name=_("Group"), linkify=True)
    tags = columns.TagColumn(url_name="tenancy:tenant_list")

    class Meta(PrimaryModelTable.Meta):
        model = Tenant
        fields = (
            "pk",
            "id",
            "name",
            "slug",
            "group",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "name", "group", "description")
