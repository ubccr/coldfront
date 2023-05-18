import logging

from django.shortcuts import reverse, redirect
from django.conf import settings

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)

MAINTENANCE_MODE_ENABLED = import_from_settings('MAINTENANCE_MODE_ENABLED', False)
MAINTENANCE_MODE_BYPASS_PASSWORD = import_from_settings('MAINTENANCE_MODE_BYPASS_PASSWORD', '')


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not MAINTENANCE_MODE_ENABLED:
            response = self.get_response(request)
            if path == reverse("maintenance"):
                response = redirect(reverse('home'))
                
            return response

        if not MAINTENANCE_MODE_BYPASS_PASSWORD:
            logger.warning('Maintenance mode is enabled but no bypass query has been set')

        # This allows the cas login to complete
        if '/user/login' in path:
            response = self.get_response(request)

        if request.GET.get('bypass_password', '') == MAINTENANCE_MODE_BYPASS_PASSWORD:
            request.session['bypass_maintenance']=True

        if not request.session.get('bypass_maintenance', False):
            if path != reverse('maintenance'):
                response = redirect(reverse('maintenance'))
                return response

        response = self.get_response(request)

        return response
