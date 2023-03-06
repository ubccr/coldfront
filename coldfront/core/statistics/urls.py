from django.urls import path

import coldfront.core.statistics.views as statistics_views

urlpatterns = [
    path('', statistics_views.SlurmJobListView.as_view(), name='slurm-job-list'),
    path('export/', statistics_views.ExportJobListView.as_view(), name='export-job-list'),
    # All URLs must come before slurm-job-detail, since it takes a
    # string as a primary key.
    path('<str:pk>/', statistics_views.SlurmJobDetailView.as_view(), name='slurm-job-detail'),
]
