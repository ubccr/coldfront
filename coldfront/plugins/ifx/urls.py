from django.urls import path, include
from rest_framework import routers, permissions
from ifxbilling.serializers import BillingRecordViewSet

router = routers.DefaultRouter()
router.register(r'billing-records', BillingRecordViewSet, 'billing-record')

urlpatterns = [
    path('api/', include(router.urls)),
]
