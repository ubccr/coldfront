from django.shortcuts import render
from django.utils.cache import add_never_cache_headers

from coldfront.plugins.maintenance_mode.utils import get_maintenance_mode_status


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not get_maintenance_mode_status():
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)

        if '/admin' in path:
            return self.get_response(request)

        # This allows the cas login to complete
        if '/user/login' in path:
            return self.get_response(request)

        response = render(
            request,
            'maintenance_mode/503.html',
            status=503
        )
        add_never_cache_headers(response)

        return response
