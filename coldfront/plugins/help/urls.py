from django.urls import path

from coldfront.plugins.help.views import get_help, send_help, get_targeted_help

urlpatterns = [
    path('', get_help, name='get-help'),
    path('<str:tgt>', get_targeted_help, name='get-targeted-help'),
    path('send', send_help, name='send_help_email'),
]
