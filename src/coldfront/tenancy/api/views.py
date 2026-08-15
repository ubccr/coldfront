# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.tenancy import filtersets
from coldfront.tenancy.models import Tenant, TenantGroup

from . import serializers


class TenancyRootView(APIRootView):
    """
    Tenancy API root view
    """

    def get_view_name(self):
        return "Tenancy"


#
# Tenants
#


class TenantGroupViewSet(ColdFrontModelViewSet):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(), Tenant, "group", "tenant_count", cumulative=True
    )
    serializer_class = serializers.TenantGroupSerializer
    filterset_class = filtersets.TenantGroupFilterSet


class TenantViewSet(ColdFrontModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = serializers.TenantSerializer
    filterset_class = filtersets.TenantFilterSet
