from django.urls import path, include
from rest_framework import routers, permissions
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')

urlpatterns = [
    path('api/', include(router.urls)),
]
