from django.urls import path

import coldfront.core.grant.views as grant_views

urlpatterns = [
    path('project/<int:project_pk>/create', grant_views.GrantCreateView.as_view(), name='grant-create'),
    path('project/<int:project_pk>/orcid-import/', grant_views.GrantOrcidImportView.as_view(), name='grant-orcid-import'),
    path('project/<int:project_pk>/orcid-import-search-result/', grant_views.GrantOrcidImportResultView.as_view(), name='grant-orcid-import-search-result'),
    # path('project/<int:project_pk>/grant-user-orcid-import/', grant_views.GrantUserOrcidImportView.as_view(), name='grant-user-orcid-import'),
    path('<int:pk>/update/', grant_views.GrantUpdateView.as_view(), name='grant-update'),
    path('project/<int:project_pk>/delete-grants/', grant_views.GrantDeleteGrantsView.as_view(), name='grant-delete-grants'),
    path('grant-report/', grant_views.GrantReportView.as_view(), name='grant-report'),
    path('grant-download/', grant_views.GrantDownloadView.as_view(), name='grant-download'),
    path('project/<int:project_pk>/create-choice/', grant_views.GrantCreateChoiceView.as_view(), name='grant-create-choice'),
]
