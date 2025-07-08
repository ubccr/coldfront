# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

from coldfront.plugins.iquota.views import get_isilon_quota

urlpatterns = [
    path("get-isilon-quota/", get_isilon_quota, name="get-isilon-quota"),
]
