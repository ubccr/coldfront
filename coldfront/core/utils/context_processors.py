from django.conf import settings


def display_time_zone(request):
    return {'DISPLAY_TIME_ZONE': settings.DISPLAY_TIME_ZONE}
