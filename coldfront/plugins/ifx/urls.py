from django.urls import path, include
from rest_framework import routers
from ifxbilling.views import unauthorized as unauthorized_api
from ifxbilling import views as ifxbilling_views
from ifxuser.views import get_org_names
from coldfront.plugins.ifx.viewsets import ColdfrontBillingRecordViewSet, ColdfrontReportRunViewSet, ColdfrontProductUsageViewSet
from coldfront.plugins.ifx.views import user_account_list, rebalance, update_user_accounts_view, get_billing_record_list, unauthorized, report_runs, run_report, calculate_billing_month, billing_month, get_product_usages, billing_records, send_billing_record_review_notification, lab_billing_summary

router = routers.DefaultRouter()
router.register(r'billing-records', ColdfrontBillingRecordViewSet, 'billing-record')
router.register(r'report-runs', ColdfrontReportRunViewSet, 'report-run')
router.register(r'product-usages', ColdfrontProductUsageViewSet, 'product-usage')

urlpatterns = [
    path('api/unauthorized/', unauthorized_api),
    path('api/billing/get-billing-record-list/', get_billing_record_list),
    path('api/billing/get-orgs-with-billing/<str:invoice_prefix>/<int:year>/<int:month>/', ifxbilling_views.get_orgs_with_billing),
    path('api/billing/get-charge-history/', ifxbilling_views.get_charge_history),
    path('api/billing/get-summary-by-user/', ifxbilling_views.get_summary_by_user),
    path('api/billing/get-summary-by-product-rate/', ifxbilling_views.get_summary_by_product_rate),
    path('api/billing/get-summary-by-account/', ifxbilling_views.get_summary_by_account),
    path('api/billing/get-pending-year-month/<str:invoice_prefix>/', ifxbilling_views.get_pending_year_month),
    path('api/billing/get-user-account-list/', user_account_list, name='user-account-list'),
    path('api/billing/rebalance/', rebalance),
    path('api/billing/calculate-billing-month/<str:invoice_prefix>/<int:year>/<int:month>/', calculate_billing_month, name='calculate-billing-month'),
    path('api/run-report/', run_report),
    path('api/get-org-names/', get_org_names, name='get-org-names'),
    path('api/get-product-usages/', get_product_usages, name='get-product-usages'),
    path('api/send-billing-record-review-notification/<int:year>/<int:month>/', send_billing_record_review_notification, name='send-billing-record-review-notification'),
    path('api/update-user-accounts/', update_user_accounts_view, name='update-user-accounts'),
    path('api/', include(router.urls)),
    path('unauthorized/', unauthorized, name='unauthorized'),
    path('report-runs/', report_runs, name='report-runs'),
    path('billing-month/', billing_month, name='billing-month'),
    path('billing-records/', billing_records, name='billing-records'),
    path('lab-billing-summary/', lab_billing_summary, name='lab-billing-summary'),
]
