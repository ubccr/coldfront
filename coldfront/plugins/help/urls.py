from django.urls import path

from coldfront.plugins.help.views import SlateProjectSearchResultsView


urlpatterns = [
    path("", SlateProjectSearchResultsView.as_view(), name="get-help"),
    path("<str:queue>", SlateProjectSearchResultsView.as_view(), name="get-help"),
]
