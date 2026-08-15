# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.SlurmRootView

# QOS
router.register("qos", views.SlurmQOSViewSet)

# Clusters
router.register("clusters", views.SlurmClusterViewSet)

# Partitions
router.register("partitions", views.SlurmPartitionViewSet)

# Accounts
router.register("accounts", views.SlurmAccountViewSet)

# Associations
router.register("associations", views.SlurmAssociationViewSet)

# Users
router.register("users", views.SlurmUserViewSet)

app_name = "slurm-api"
urlpatterns = router.urls
