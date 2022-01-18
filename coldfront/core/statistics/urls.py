from django.urls import path

import coldfront.core.statistics.views as statistics_views

urlpatterns = [
    path('', statistics_views.SlurmJobListView.as_view(), name='slurm-job-list'),
    path('<int:pk>/', statistics_views.SlurmJobDetailView.as_view(), name='slurm-job-detail'),
]