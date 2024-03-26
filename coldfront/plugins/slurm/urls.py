from django.urls import path

from coldfront.plugins.slurm.views import get_all_slurm_submission_info, get_slurm_submission_info

urlpatterns = [
    path('all-slurm-submission-info/', get_all_slurm_submission_info, name='all-slurm-submission-info'),
    path('slurm-submission-info/', get_slurm_submission_info, name='slurm-submission-info')
]
