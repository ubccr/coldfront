# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.BillingRootView

# Invoices
router.register("invoices", views.InvoiceViewSet)

# Invoice line items
router.register("invoice-line-items", views.InvoiceLineItemViewSet)

# Rates
router.register("rates", views.RateViewSet)

# Free allowances
router.register("free-allowances", views.FreeAllowanceViewSet)

# Discounts
router.register("discounts", views.DiscountViewSet)

app_name = "billing-api"
urlpatterns = router.urls
