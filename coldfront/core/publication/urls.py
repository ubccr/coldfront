from django.urls import path

from coldfront.core.utils.common import import_from_settings
PUBLICATION_ENABLE = import_from_settings('PUBLICATION_ENABLE', False)

if PUBLICATION_ENABLE:
    import coldfront.core.publication.views as publication_views

    urlpatterns = [
        path('publication-search/<int:project_pk>/', publication_views.PublicationSearchView.as_view(), name='publication-search'),
        path('publication-search-result/<int:project_pk>/', publication_views.PublicationSearchResultView.as_view(), name='publication-search-result'),
        path('add-publication/<int:project_pk>/', publication_views.PublicationAddView.as_view(), name='add-publication'),
        path('add-publication-manually/<int:project_pk>/', publication_views.PublicationAddManuallyView.as_view(), name='add-publication-manually'),
        path('project/<int:project_pk>/delete-publications/', publication_views.PublicationDeletePublicationsView.as_view(), name='publication-delete-publications'),
        path('project/<int:project_pk>/export-publications/', publication_views.PublicationExportPublicationsView.as_view(), name='publication-export-publications'),
    ]

else:
    urlpatterns = []