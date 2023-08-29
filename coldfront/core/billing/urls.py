from flags.urls import flagged_paths

from coldfront.core.billing.views import admin_views


urlpatterns = []


with flagged_paths('LRC_ONLY') as path:
    flagged_url_patterns = [
        path('usages/',
             admin_views.BillingIDUsagesSearchView.as_view(),
             name='billing-id-usages'),
    ]


urlpatterns += flagged_url_patterns
