from django.urls import path

from coldfront.plugins.slate_project.views import (get_slate_project_info,
                                                   get_slate_project_estimated_cost,
                                                   slate_project_search_view,
                                                   validate_project_directory_name,
                                                   SlateProjectSearchResultsView,
                                                   RequestAccessEmailView)

urlpatterns = [
    path('get_slate_project_info/', get_slate_project_info, name='get-slate-project-info'),
    path('get_estimated_slate_project_cost/', get_slate_project_estimated_cost, name='get-estimated-slate-project-cost'),
    path('slate_project_search/', slate_project_search_view, name="slate-project-search"),
    path('slate_project_search_results/', SlateProjectSearchResultsView.as_view(), name="slate-project-search-results"),
    path('send_slate_project_access_request/', RequestAccessEmailView.as_view(), name='send-slate-project-access-request'),
    path('validate_directory_name/', validate_project_directory_name, name='validate-directory-name'),
]
