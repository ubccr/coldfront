# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.CoreRootView

router.register("custom-fields", views.CustomFieldViewSet)
router.register("custom-field-choice-sets", views.CustomFieldChoiceSetViewSet)
router.register("saved-filters", views.SavedFilterViewSet)
router.register("tags", views.TagViewSet)
router.register("table-configs", views.TableConfigViewSet)
router.register("tagged-objects", views.TaggedItemViewSet)

app_name = "core-api"
urlpatterns = router.urls
