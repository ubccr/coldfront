# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

import coldfront.core.allocation.views as allocation_views
from coldfront.config.core import ALLOCATION_EULA_ENABLE

urlpatterns = [
    path("", allocation_views.AllocationListView.as_view(), name="allocation-list"),
    path("project/<int:project_pk>/create", allocation_views.AllocationCreateView.as_view(), name="allocation-create"),
    path("<int:pk>/", allocation_views.AllocationDetailView.as_view(), name="allocation-detail"),
    path(
        "change-request/<int:pk>/",
        allocation_views.AllocationChangeDetailView.as_view(),
        name="allocation-change-detail",
    ),
    path(
        "<int:pk>/delete-attribute-change",
        allocation_views.AllocationChangeDeleteAttributeView.as_view(),
        name="allocation-attribute-change-delete",
    ),
    path("<int:pk>/add-users", allocation_views.AllocationAddUsersView.as_view(), name="allocation-add-users"),
    path("<int:pk>/remove-users", allocation_views.AllocationRemoveUsersView.as_view(), name="allocation-remove-users"),
    path("request-list", allocation_views.AllocationRequestListView.as_view(), name="allocation-request-list"),
    path("change-list", allocation_views.AllocationChangeListView.as_view(), name="allocation-change-list"),
    path("<int:pk>/renew", allocation_views.AllocationRenewView.as_view(), name="allocation-renew"),
    path(
        "<int:pk>/allocationattribute/add",
        allocation_views.AllocationAttributeCreateView.as_view(),
        name="allocation-attribute-add",
    ),
    path("<int:pk>/change-request", allocation_views.AllocationChangeView.as_view(), name="allocation-change"),
    path(
        "<int:pk>/allocationattribute/delete",
        allocation_views.AllocationAttributeDeleteView.as_view(),
        name="allocation-attribute-delete",
    ),
    path(
        "<int:pk>/allocationnote/add", allocation_views.AllocationNoteCreateView.as_view(), name="allocation-note-add"
    ),
    path(
        "allocation-invoice-list", allocation_views.AllocationInvoiceListView.as_view(), name="allocation-invoice-list"
    ),
    path("<int:pk>/invoice/", allocation_views.AllocationInvoiceDetailView.as_view(), name="allocation-invoice-detail"),
    path(
        "allocation/<int:pk>/add-invoice-note",
        allocation_views.AllocationAddInvoiceNoteView.as_view(),
        name="allocation-add-invoice-note",
    ),
    path(
        "allocation-invoice-note/<int:pk>/update",
        allocation_views.AllocationUpdateInvoiceNoteView.as_view(),
        name="allocation-update-invoice-note",
    ),
    path(
        "allocation/<int:pk>/invoice/delete/",
        allocation_views.AllocationDeleteInvoiceNoteView.as_view(),
        name="allocation-delete-invoice-note",
    ),
    path(
        "add-allocation-account/", allocation_views.AllocationAccountCreateView.as_view(), name="add-allocation-account"
    ),
    path(
        "allocation-account-list/", allocation_views.AllocationAccountListView.as_view(), name="allocation-account-list"
    ),
]

if ALLOCATION_EULA_ENABLE:
    urlpatterns.append(
        path("<int:pk>/review-eula", allocation_views.AllocationEULAView.as_view(), name="allocation-review-eula")
    )
