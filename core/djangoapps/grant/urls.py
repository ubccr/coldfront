from django.urls import path

import core.djangoapps.grant.views as grant_views

urlpatterns = [
    path('project/<int:project_pk>/create', grant_views.GrantCreateView.as_view(), name='grant-create'),
    path('<int:pk>/update/', grant_views.GrantUpdateView.as_view(), name='grant-update'),
    path('project/<int:project_pk>/delete-grants/', grant_views.GrantDeleteGrantsView.as_view(), name='grant-delete-grants'),
]
