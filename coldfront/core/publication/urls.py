from django.urls import path

import coldfront.core.publication.views as publication_views

urlpatterns = [
    path('publication-search/<int:project_pk>/', publication_views.PublicationSearchView.as_view(), name='publication-search'),
    path('publication-search-result/<int:project_pk>/', publication_views.PublicationSearchResultView.as_view(), name='publication-search-result'),
    path('add-publication/<int:project_pk>/', publication_views.PublicationAddView.as_view(), name='add-publication'),
    path('add-publication-manually/<int:project_pk>/', publication_views.PublicationAddManuallyView.as_view(), name='add-publication-manually'),
    path('user-orcid-import/<int:project_pk>/', publication_views.PublicationImportUserOrcidHome.as_view(), name='user-orcid-import'),
    path('user-orcid-import-result/<int:project_pk>/', publication_views.PublicationImportUserOrcidResult.as_view(), name='user-orcid-import-result'),
    path('project/<int:project_pk>/delete-publications/', publication_views.PublicationDeletePublicationsView.as_view(), name='publication-delete-publications'),
    path('project/<int:project_pk>/export-publications/', publication_views.PublicationExportPublicationsView.as_view(), name='publication-export-publications'),
]
