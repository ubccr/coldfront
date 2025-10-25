# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.views.generic import TemplateView

# Get an instance of a logger
logger = logging.getLogger(__name__)


class MaintenanceView(TemplateView):
    template_name = "maintenance_mode/maintenance_page.html"

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)

        message = self.request.session.pop("message", None)
        context["message"] = message

        return context
