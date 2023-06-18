from django.urls import path

import coldfront.core.research_output.views as research_output_views

urlpatterns = [
    path('add-research-output/<int:project_pk>/', research_output_views.ResearchOutputCreateView.as_view(), name='add-research-output'),
    path('project/<int:project_pk>/delete-research-outputs', research_output_views.ResearchOutputDeleteResearchOutputsView.as_view(), name='research-output-delete-research-outputs'),
    path('research-output-report/', research_output_views.ResearchOutputReportView.as_view(), name='research-output-report'),

]
