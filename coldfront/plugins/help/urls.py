from django.urls import path

from coldfront.plugins.help.views import HelpView


urlpatterns = [
    path("", HelpView.as_view(), name="get-help"),
]
