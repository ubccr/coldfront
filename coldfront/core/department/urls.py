from django.urls import path

import coldfront.core.department.views as dept_views

urlpatterns = [
    path('', dept_views.DepartmentListView.as_view(), name='department-list'),
    path(
        '<int:pk>/', dept_views.DepartmentDetailView.as_view(), name='department-detail'
    ),
    path('<int:pk>/departmentnote/add', dept_views.DepartmentNoteCreateView.as_view(), name='department-note-add'),
    path(
        'department-note/<int:pk>/update',
        dept_views.DepartmentNoteUpdateView.as_view(), name='department-note-update'
    ),

]
