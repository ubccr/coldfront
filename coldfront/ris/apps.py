# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RisConfig(AppConfig):
    name = "coldfront.ris"
    label = "ris"
    verbose_name = _("Research Information System")

    def ready(self):
        from coldfront.models.features import register_models

        register_models(*self.get_models())

        from . import views  # noqa: F401
