from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, reverse_lazy, include

import coldfront.core.user.views as user_views

EXTRA_APPS = settings.INSTALLED_APPS


urlpatterns = [
    path('login',
         LoginView.as_view(
             template_name='user/login.html',
             extra_context={'EXTRA_APPS': EXTRA_APPS},
             redirect_authenticated_user=True),
         name='login'
         ),
    path('logout', LogoutView.as_view(), name='logout'),
    path('user-profile/', user_views.UserProfileView.as_view(), name='user-profile'),
    path('user-profile/<str:viewed_username>', user_views.UserProfileView.as_view(), name='user-profile'),
    path('user-projects-managers/', user_views.UserProjectsManagersView.as_view(), name='user-projects-managers'),
    path('user-projects-managers/<str:viewed_username>', user_views.UserProjectsManagersView.as_view(), name='user-projects-managers'),
    path('user-upgrade/', user_views.UserUpgradeAccount.as_view(), name='user-upgrade'),
    path('user-search-home/', user_views.UserSearchHome.as_view(), name='user-search-home'),
    path('user-search-results/', user_views.UserSearchResults.as_view(), name='user-search-results'),
    path('user-select-home/', user_views.UserSelectHome.as_view(), name='user-select-home'),
    path('user-select-results/', user_views.UserSelectResults.as_view(), name='user-select-results'),
    path('user-list-allocations/', user_views.UserListAllocations.as_view(), name='user-list-allocations'),
 
]
