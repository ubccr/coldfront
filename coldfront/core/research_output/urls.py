# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.urls import path

import coldfront.core.research_output.views as research_output_views

urlpatterns = [
    path(
        "add-research-output/<int:project_pk>/",
        research_output_views.ResearchOutputCreateView.as_view(),
        name="add-research-output",
    ),
    path(
        "project/<int:project_pk>/delete-research-outputs",
        research_output_views.ResearchOutputDeleteResearchOutputsView.as_view(),
        name="research-output-delete-research-outputs",
    ),
]
