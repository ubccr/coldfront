# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa F401

app_name = "tenancy"
urlpatterns = [
    path("tenant-groups/", include(get_model_urls("tenancy", "tenantgroup", detail=False))),
    path("tenant-groups/<int:pk>/", include(get_model_urls("tenancy", "tenantgroup"))),
    path("tenants/", include(get_model_urls("tenancy", "tenant", detail=False))),
    path("tenants/<int:pk>/", include(get_model_urls("tenancy", "tenant"))),
]
