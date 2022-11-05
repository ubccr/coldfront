from rest_framework.routers import DefaultRouter

from coldfront.api.billing.views import BillingActivityViewSet


router = DefaultRouter()

router.register(
    r'billing_activities', BillingActivityViewSet,
    basename='billing_activities')

urlpatterns = router.urls
