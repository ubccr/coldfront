from django.conf.urls import url
from django.urls import include


urlpatterns = [
    url(r'^', include('coldfront.api.allocation.urls')),
    url(r'^', include('coldfront.api.statistics.urls')),
    url(r'^', include('coldfront.api.project.urls')),
    url(r'^', include('coldfront.api.user.urls')),
    url(r'^', include('coldfront.api.utils.urls')),
]
