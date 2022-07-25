from django.urls import path, include
from rest_framework import routers
from ifxbilling.views import unauthorized as unauthorized_api
from ifxbilling.views import get_billing_record_list
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet
from coldfront.plugins.ifx.views import unauthorized

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')

urlpatterns = [
    path('api/unauthorized/', unauthorized_api),
    path('api/billing/get-billing-record-list/', get_billing_record_list),
    path('api/', include(router.urls)),
    path('unauthorized/', unauthorized, name='unauthorized'),
]
