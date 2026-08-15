# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import include, path

from coldfront.registry import get_model_urls

from . import views  # noqa F401

app_name = "slurm"
urlpatterns = [
    path("qos/", include(get_model_urls("slurm", "slurmqos", detail=False))),
    path("qos/<int:pk>/", include(get_model_urls("slurm", "slurmqos"))),
    path("clusters/", include(get_model_urls("slurm", "slurmcluster", detail=False))),
    path("clusters/<int:pk>/", include(get_model_urls("slurm", "slurmcluster"))),
    path("partitions/", include(get_model_urls("slurm", "slurmpartition", detail=False))),
    path("partitions/<int:pk>/", include(get_model_urls("slurm", "slurmpartition"))),
    path("accounts/", include(get_model_urls("slurm", "slurmaccount", detail=False))),
    path("accounts/<int:pk>/", include(get_model_urls("slurm", "slurmaccount"))),
    path("associations/", include(get_model_urls("slurm", "slurmassociation", detail=False))),
    path("associations/<int:pk>/", include(get_model_urls("slurm", "slurmassociation"))),
    path("users/", include(get_model_urls("slurm", "slurmuser", detail=False))),
    path("users/<int:pk>/", include(get_model_urls("slurm", "slurmuser"))),
]
