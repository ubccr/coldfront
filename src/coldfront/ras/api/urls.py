# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.RASRootView

# Projects
router.register("projects", views.ProjectViewSet)
router.register("project-users", views.ProjectUserViewSet)

# Resources
router.register("resources", views.ResourceViewSet)
router.register("resource-types", views.ResourceTypeViewSet)

# Allocations
router.register("allocations", views.AllocationViewSet)

# Change Requests
router.register("change-requests", views.AllocationChangeRequestViewSet)


app_name = "ras-api"
urlpatterns = router.urls
