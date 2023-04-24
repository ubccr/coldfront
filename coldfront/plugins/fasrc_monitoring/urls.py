from django.urls import path, include
from rest_framework import routers
from coldfront.plugins.fasrc_monitoring.views import MonitorView

router = routers.DefaultRouter()

urlpatterns = [
    path('monitor', MonitorView.as_view(), name='monitor'),
]
