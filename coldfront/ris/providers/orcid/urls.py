# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import path

from . import views

urlpatterns = [
    path("link/", views.OrcidLinkView.as_view(), name="link"),
    path("callback/", views.OrcidCallbackView.as_view(), name="callback"),
    path("unlink/", views.OrcidUnlinkView.as_view(), name="unlink"),
]
