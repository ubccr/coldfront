from django.urls import path

from coldfront.plugins.customizable_forms.views import AllocationResourceSelectionView, DispatchView


urlpatterns = [
    path(
        'project/<int:project_pk>/create/',
        AllocationResourceSelectionView.as_view(),
        name='custom-allocation-create'
    ),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>',
        DispatchView.as_view(),
        name='resource-form-redirector'
    ),
]
