from django.urls import path
from coldfront.plugins.customizable_forms.custom.views import ComputeView, PositConnectView, SlateProjectView, GeodeProjectForm


urlpatterns = [
    path(
        '<int:project_pk>/create/<int:resource_pk>/quartz',
        ComputeView.as_view(),
        name='quartz-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/bigred200',
        ComputeView.as_view(),
        name='bigred200-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/positconnect',
        PositConnectView.as_view(),
        name='posit-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/slateproject',
        SlateProjectView.as_view(),
        name='slateproject-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/geode-projects',
        GeodeProjectForm.as_view(),
        name='geodeproject-form'
    ),
]