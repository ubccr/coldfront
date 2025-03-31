from django.urls import path

from coldfront.plugins.movable_allocations.views import (
    AllocationMoveView,
    ProjectDetailView,
)

urlpatterns = [
    path("<int:pk>/move-allocation", AllocationMoveView.as_view(), name="move-allocation"),
    path("<int:pk>/project-info/<int:project_pk>", ProjectDetailView.as_view(), name="project-info"),
]
