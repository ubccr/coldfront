# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.RISRootView

# Publications
router.register("publications", views.PublicationViewSet)

# Funding
router.register("funding", views.FundingViewSet)

app_name = "ris-api"
urlpatterns = router.urls
