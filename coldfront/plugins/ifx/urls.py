from django.urls import path, include
from rest_framework import routers
from ifxbilling.views import unauthorized as unauthorized_api
from ifxbilling.views import get_billing_record_list
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet, ColdfrontReportRunViewSet, ColdfrontProductUsageViewSet
from coldfront.plugins.ifx.views import unauthorized, report_runs, run_report, calculate_billing_month, billing_month, get_product_usages, billing_records

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')
router.register(r'report-runs', ColdfrontReportRunViewSet, 'report-run')
router.register(r'product-usages', ColdfrontProductUsageViewSet, 'product-usage')

urlpatterns = [
    path('api/unauthorized/', unauthorized_api),
    path('api/billing/get-billing-record-list/', get_billing_record_list),
    path('api/calculate-billing-month/<int:year>/<int:month>/', calculate_billing_month),
    path('api/run-report/', run_report),
    path('api/get-product-usages/', get_product_usages, name='get-product-usages'),
    path('api/', include(router.urls)),
    path('unauthorized/', unauthorized, name='unauthorized'),
    path('report-runs/', report_runs, name='report-runs'),
    path('billing-month/', billing_month, name='billing-month'),
    path('billing-records/', billing_records, name='billing-records'),
]
