# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404
from coldfront.plugins.maintenance_mode.utils import get_maintenance_state
from coldfront.core.utils.common import import_from_settings
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

MAINTENANCE_EXCLUDED_USERS = import_from_settings("MAINTENANCE_EXCLUDED_USERS")


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check for an active maintenance window
        status, message = get_maintenance_state()

        # only redirect if there is maintenance and the page is not
        # already the maintenance page
        if status and request.path != reverse("maintenance_page"):
            if request.user.username not in MAINTENANCE_EXCLUDED_USERS:
                request.session["message"] = message
                return redirect("maintenance_page")
        elif not status and request.path == reverse("maintenance_page"):
            raise Http404("Page does not exist")

        if status and message:
            request.session["message"] = message

        response = self.get_response(request)
        return response
