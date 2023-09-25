from django.urls import path

from coldfront.plugins.slurm.views import get_slurm_accounts

urlpatterns = [
    path('get-slurm-accounts/', get_slurm_accounts, name='get-slurm-accounts'),
]
