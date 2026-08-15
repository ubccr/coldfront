# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa F401

app_name = "users"
urlpatterns = [
    path("users/", include(get_model_urls("users", "user", detail=False))),
    path("users/<int:pk>/", include(get_model_urls("users", "user"))),
    path("groups/", include(get_model_urls("users", "group", detail=False))),
    path("groups/<int:pk>/", include(get_model_urls("users", "group"))),
    path("roles/", include(get_model_urls("users", "role", detail=False))),
    path("roles/<int:pk>/", include(get_model_urls("users", "role"))),
    path("permissions/", include(get_model_urls("users", "objectpermission", detail=False))),
    path("permissions/<int:pk>/", include(get_model_urls("users", "objectpermission"))),
    path("tokens/", include(get_model_urls("users", "token", detail=False))),
    path("tokens/<int:pk>/", include(get_model_urls("users", "token"))),
]
