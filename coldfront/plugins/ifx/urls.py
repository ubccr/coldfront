from django.urls import path, include
from django.conf import settings
from rest_framework import routers
from ifxbilling.views import unauthorized as unauthorized_api
from ifxbilling.views import get_billing_record_list
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet, ColdfrontReportRunViewSet
from coldfront.plugins.ifx.views import unauthorized, report_runs, run_report

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')
router.register(r'report-runs', ColdfrontReportRunViewSet, 'report-run')

urlpatterns = [
    path('api/unauthorized/', unauthorized_api),
    path('api/billing/get-billing-record-list/', get_billing_record_list),
    path('api/run-report/', run_report),
    path('api/', include(router.urls)),
    path('unauthorized/', unauthorized, name='unauthorized'),
    path('report-runs/', report_runs, name='report-runs'),
]
