from django.urls import path

import coldfront.core.research_output.views as research_output_views

urlpatterns = [
    path('add-research-output/<int:project_pk>/', research_output_views.ResearchOutputCreateView.as_view(), name='add-research-output'),
]
