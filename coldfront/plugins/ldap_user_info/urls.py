from django.urls import path

from coldfront.plugins.ldap_user_info.views import LDAPUserSearchView

urlpatterns = [
    path('ldap_user_search/', LDAPUserSearchView.as_view(), name='ldap-user-search'),
]
