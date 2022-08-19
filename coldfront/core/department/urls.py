from django.urls import path

import coldfront.core.department.views as dept_views

urlpatterns = [
    path('', dept_views.DepartmentListView.as_view(), name='department-list'),
    path('<int:pk>/', dept_views.DepartmentDetailView.as_view(), name="department-detail")
]
