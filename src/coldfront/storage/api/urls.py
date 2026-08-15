# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.StorageRootView

# Snapshot policies
router.register("snapshot-policies", views.StorageSnapshotPolicyViewSet)

# Clusters
router.register("clusters", views.StorageClusterViewSet)

# Resources
router.register("resources", views.StorageResourceViewSet)

# Quotas
router.register("quotas", views.StorageQuotaViewSet)

app_name = "storage-api"
urlpatterns = router.urls
