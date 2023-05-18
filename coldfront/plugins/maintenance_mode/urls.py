from django.urls import path

from coldfront.plugins.maintenance_mode.views import maintenance


urlpatterns = [
    path('maintenance/', maintenance, name='maintenance')
]
