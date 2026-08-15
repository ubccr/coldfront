# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SlurmConfig(AppConfig):
    name = "coldfront.slurm"
    label = "slurm"
    verbose_name = _("Slurm")

    def ready(self):
        from coldfront.models.features import register_models

        register_models(*self.get_models())

        from . import (
            listeners,  # noqa: F401
            views,  # noqa: F401
        )
