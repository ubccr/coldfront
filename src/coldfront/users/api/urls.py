# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.api.routers import ColdFrontRouter

from . import views

router = ColdFrontRouter()
router.APIRootView = views.UsersRootView

router.register("users", views.UserViewSet)
router.register("groups", views.GroupViewSet)
router.register("roles", views.RoleViewSet)
router.register("tokens", views.TokenViewSet)
router.register("permissions", views.ObjectPermissionViewSet)
router.register("config", views.UserConfigViewSet, basename="userconfig")

app_name = "users-api"
urlpatterns = [
    path("tokens/provision/", views.TokenProvisionView.as_view(), name="token_provision"),
    path("", include(router.urls)),
]
