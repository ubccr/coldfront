from django.urls import path

import coldfront.core.research_output.views as research_output_views
from coldfront.core.utils.common import import_from_settings
RESEARCH_OUTPUT_ENABLE = import_from_settings("RESEARCH_OUTPUT_ENABLE", True)

if not RESEARCH_OUTPUT_ENABLE:
    urlpatterns = []
else:
    urlpatterns = [
        path('add-research-output/<int:project_pk>/', research_output_views.ResearchOutputCreateView.as_view(), name='add-research-output'),
        path('project/<int:project_pk>/delete-research-outputs', research_output_views.ResearchOutputDeleteResearchOutputsView.as_view(), name='research-output-delete-research-outputs'),
    ]
