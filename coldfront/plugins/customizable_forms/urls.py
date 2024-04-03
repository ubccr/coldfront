from django.urls import path

from coldfront.plugins.customizable_forms.views import (AllocationResourceSelectionView,
                                                        GenericView,
                                                        DispatchView,
                                                        ComputeView,
                                                        PositConnectView,
                                                        SlateProjectView)

urlpatterns = [
    path(
        'project/<int:project_pk>/create/',
        AllocationResourceSelectionView.as_view(),
        name='custom-allocation-create'
    ),
    # path(
    #     'project/<int:project_pk>/create/',
    #     BaseAllocationCreateView.as_view(),
    #     name='custom-allocation-create'
    # ),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>',
        DispatchView.as_view(),
        name='resource-form-redirector'
    ),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>/quartz',
        ComputeView.as_view(),
        name='quartz-form'
    ),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>/bigred200',
        ComputeView.as_view(),
        name='bigred200-form'
    ),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>/positconnect',
        PositConnectView.as_view(),
        name='posit-form'
    ),
    # All new custom forms should be put above this line
    path(
        'project/<int:project_pk>/create/<int:resource_pk>/<str:resource_name>',
        GenericView.as_view(),
        name='resource-form'
    ),
]