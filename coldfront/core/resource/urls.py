# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

import coldfront.core.resource.views as resource_views

urlpatterns = [
    path("", resource_views.ResourceListView.as_view(), name="resource-list"),
    path("<int:pk>/", resource_views.ResourceDetailView.as_view(), name="resource-detail"),
    path(
        "<int:pk>/resourceattribute/add",
        resource_views.ResourceAttributeCreateView.as_view(),
        name="resource-attribute-add",
    ),
    path(
        "<int:pk>/resourceattribute/delete",
        resource_views.ResourceAttributeDeleteView.as_view(),
        name="resource-attribute-delete",
    ),
]
