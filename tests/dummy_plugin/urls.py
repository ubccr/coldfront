# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import path

from . import views

urlpatterns = [
    path("models/", views.DummyModelsView.as_view(), name="dummy_model_list"),
    path("models/add/", views.DummyModelAddView.as_view(), name="dummy_model_add"),
    path("coldfrontmodel/", views.DummyColdFrontModelView.as_view(), name="dummycoldfrontmodel_list"),
    path("coldfrontmodel/add/", views.DummyColdFrontModelView.as_view(), name="dummycoldfrontmodel_add"),
    path("coldfrontmodel/import/", views.DummyColdFrontModelView.as_view(), name="dummycoldfrontmodel_bulk_import"),
    path("coldfrontmodel/<int:pk>/", views.DummyColdFrontModelView.as_view(), name="dummycoldfrontmodel"),
]
