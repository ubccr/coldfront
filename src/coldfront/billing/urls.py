# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa: F401

app_name = "billing"
urlpatterns = [
    path("invoices/", include(get_model_urls("billing", "invoice", detail=False))),
    path("invoices/<int:pk>/", include(get_model_urls("billing", "invoice"))),
    path("line-items/", include(get_model_urls("billing", "invoicelineitem", detail=False))),
    path("line-items/<int:pk>/", include(get_model_urls("billing", "invoicelineitem"))),
    path("rates/", include(get_model_urls("billing", "rate", detail=False))),
    path("rates/<int:pk>/", include(get_model_urls("billing", "rate"))),
    path("free-allowances/", include(get_model_urls("billing", "freeallowance", detail=False))),
    path("free-allowances/<int:pk>/", include(get_model_urls("billing", "freeallowance"))),
    path("discounts/", include(get_model_urls("billing", "discount", detail=False))),
    path("discounts/<int:pk>/", include(get_model_urls("billing", "discount"))),
]
