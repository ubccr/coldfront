# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa F401

app_name = "ras"
urlpatterns = [
    path("resource-types/", include(get_model_urls("ras", "resourcetype", detail=False))),
    path("resource-types/<int:pk>/", include(get_model_urls("ras", "resourcetype"))),
    path("resources/", include(get_model_urls("ras", "resource", detail=False))),
    path("resources/<int:pk>/", include(get_model_urls("ras", "resource"))),
    path("projects/", include(get_model_urls("ras", "project", detail=False))),
    path("projects/<int:pk>/", include(get_model_urls("ras", "project"))),
    path("project-users/", include(get_model_urls("ras", "projectuser", detail=False))),
    path("project-users/<int:pk>/", include(get_model_urls("ras", "projectuser"))),
    path("allocations/", include(get_model_urls("ras", "allocation", detail=False))),
    path("allocations/<int:pk>/", include(get_model_urls("ras", "allocation"))),
    path("change-requests/", include(get_model_urls("ras", "allocationchangerequest", detail=False))),
    path("change-requests/<int:pk>/", include(get_model_urls("ras", "allocationchangerequest"))),
]
