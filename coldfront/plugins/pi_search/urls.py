from django.urls import path

from coldfront.plugins.pi_search.views import PISearchResultsView, pi_search_view, RequestAccessEmailView


urlpatterns = [
    path('pi_search/', pi_search_view, name="pi-search"),
    path('pi_search_results/', PISearchResultsView.as_view(), name="pi-search-results"),
    path('send-access-request/', RequestAccessEmailView.as_view(),name='send-access-request'),
]