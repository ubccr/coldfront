from django.urls import path

from coldfront.plugins.help.views import get_help, send_help, get_targeted_help
from django.views.decorators.http import require_POST

urlpatterns = [
    path('send', require_POST(send_help), name='send_help_email'),
    path('', get_help, name='get-help'),
    path('<str:tgt>', get_targeted_help, name='get-targeted-help'),
] 
