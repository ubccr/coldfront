from django.urls import path

from coldfront.plugins.slate_project.views import get_slate_project_info, get_slate_project_estimated_cost

urlpatterns = [
    path('get_slate_project_info/', get_slate_project_info, name='get-slate-project-info'),
    path('get_estimated_slate_project_cost/', get_slate_project_estimated_cost, name='get-estimated-slate-project-cost')
]
