from django.urls import include, path

from coldfront.plugins.iquota.views import get_isilon_quota


urlpatterns = [
    path(
        "iquota/", include([path('get-isilon-quota/', get_isilon_quota, name='get-isilon-quota')]),
    ),
]
