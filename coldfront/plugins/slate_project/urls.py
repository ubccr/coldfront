from django.urls import path

from coldfront.plugins.slate_project.views import (get_slate_project_info,
                                                   get_slate_project_estimated_cost,
                                                   slate_project_search_view,
                                                   SlateProjectSearchResultsView,
                                                   RequestAccessEmailView)

urlpatterns = [
    path('get_slate_project_info/', get_slate_project_info, name='get-slate-project-info'),
    path('get_estimated_slate_project_cost/', get_slate_project_estimated_cost, name='get-estimated-slate-project-cost'),
    path('slate_project_search/', slate_project_search_view, name="slate-project-search"),
    path('slate_project_search_results/', SlateProjectSearchResultsView.as_view(), name="slate-project-search-results"),
    path('send-slate-project-access-request/', RequestAccessEmailView.as_view(), name='send-slate-project-access-request'),
]
