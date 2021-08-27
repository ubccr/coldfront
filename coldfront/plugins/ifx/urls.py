from django.urls import path, include
from rest_framework import routers
from ifxbilling.views import unauthorized as unauthorized_api
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet
from coldfront.plugins.ifx.views import unauthorized

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')

urlpatterns = [
    path('api/unauthorized/', unauthorized_api),
    path('api/', include(router.urls)),
    path('unauthorized/', unauthorized),
]
