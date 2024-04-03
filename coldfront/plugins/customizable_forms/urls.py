from django.urls import path, include

from coldfront.plugins.customizable_forms.views import (AllocationResourceSelectionView,
                                                        GenericView,
                                                        DispatchView)

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
    path('project/', include('coldfront.plugins.customizable_forms.custom.urls')),
    path(
        'project/<int:project_pk>/create/<int:resource_pk>/<str:resource_name>',
        GenericView.as_view(),
        name='resource-form'
    ),
]
