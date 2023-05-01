from django.urls import path

import coldfront.core.grant.views as grant_views

from coldfront.core.utils.common import import_from_settings

GRANT_ENABLE = import_from_settings("GRANT_ENABLE", True)

if GRANT_ENABLE:
    urlpatterns = [
        path('project/<int:project_pk>/create', grant_views.GrantCreateView.as_view(), name='grant-create'),
        path('<int:pk>/update/', grant_views.GrantUpdateView.as_view(), name='grant-update'),
        path('project/<int:project_pk>/delete-grants/', grant_views.GrantDeleteGrantsView.as_view(), name='grant-delete-grants'),
        path('grant-report/', grant_views.GrantReportView.as_view(), name='grant-report'),
        path('grant-download/', grant_views.GrantDownloadView.as_view(), name='grant-download'),
    ]
else:
    urlpatterns = []
