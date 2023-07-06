from django.urls import path

from coldfront.plugins.slate_project_info.views import get_slate_project_info

urlpatterns = [
    path('get_slate_project_info/', get_slate_project_info, name='get-slate-project-info'),
]
