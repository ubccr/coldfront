# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa: F401

app_name = "storage"
urlpatterns = [
    path("resources/", include(get_model_urls("storage", "storageresource", detail=False))),
    path("resources/<int:pk>/", include(get_model_urls("storage", "storageresource"))),
    path("clusters/", include(get_model_urls("storage", "storagecluster", detail=False))),
    path("clusters/<int:pk>/", include(get_model_urls("storage", "storagecluster"))),
    path("quotas/", include(get_model_urls("storage", "storagequota", detail=False))),
    path("quotas/<int:pk>/", include(get_model_urls("storage", "storagequota"))),
    path("snapshot-policies/", include(get_model_urls("storage", "storagesnapshotpolicy", detail=False))),
    path("snapshot-policies/<int:pk>/", include(get_model_urls("storage", "storagesnapshotpolicy"))),
]
