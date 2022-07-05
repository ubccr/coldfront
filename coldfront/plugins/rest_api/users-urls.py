
from django.urls import include, path

from django.urls import path, include
from django.contrib.auth.models import User
from coldfront.icm.account_applications.models import AccountApplication, AccountApplicationsStatusChoice
from rest_framework import routers, serializers, viewsets
from rest_framework.authtoken import views
from coldfront.plugins.rest_api.views import SLURMAccountsAPI, show_auth_code

from rest_framework import generics


urlpatterns = [
    path('slurm/<str:cluster>/', SLURMAccountsAPI.as_view(), name='user-slurm-accounts'),
    path('o/showcode', show_auth_code, name='show-auth-code'),
]

