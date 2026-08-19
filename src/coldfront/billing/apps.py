# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BillingConfig(AppConfig):
    name = "coldfront.billing"
    label = "billing"
    verbose_name = _("Billing")

    def ready(self):
        from coldfront.models.features import register_models

        register_models(*self.get_models())

        from . import (
            views,  # noqa: F401
        )
