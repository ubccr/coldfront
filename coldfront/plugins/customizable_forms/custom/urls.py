from django.urls import path
from coldfront.plugins.customizable_forms.custom.views import ComputeView, PositConnectView


urlpatterns = [
    path(
        '<int:project_pk>/create/<int:resource_pk>/Quartz',
        ComputeView.as_view(),
        name='quartz-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/BigRed200',
        ComputeView.as_view(),
        name='bigred200-form'
    ),
    path(
        '<int:project_pk>/create/<int:resource_pk>/PositConnect',
        PositConnectView.as_view(),
        name='positconnect-form'
    ),
]