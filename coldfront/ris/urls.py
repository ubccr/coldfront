# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa: F401

app_name = "ris"
urlpatterns = [
    path("publications/", include(get_model_urls("ris", "publication", detail=False))),
    path("publications/<int:pk>/", include(get_model_urls("ris", "publication"))),
    path("funding/", include(get_model_urls("ris", "funding", detail=False))),
    path("funding/<int:pk>/", include(get_model_urls("ris", "funding"))),
]
