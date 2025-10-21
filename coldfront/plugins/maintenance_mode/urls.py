# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path
from coldfront.plugins.maintenance_mode.views import MaintenanceView

urlpatterns = [
    path("", MaintenanceView.as_view(), name="maintenance_page"),
]
