# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "coldfront.core"

    def ready(self):
        import django.db.models as dj_models

        from coldfront.lib.constants import COLDFRONT_BLANK_CHOICE_LABEL

        # Override BLANK_CHOICE_LABEL so every auto-generated ModelChoiceField
        # empty_label (and any get_blank_choice_label() consumer) uses our stock
        # blank label instead.
        dj_models.fields.BLANK_CHOICE_LABEL = COLDFRONT_BLANK_CHOICE_LABEL

        from coldfront.lib import context_processors  # noqa: F401
        from coldfront.lib.models.features import register_models

        from . import (
            notifications,  # noqa: F401
            signals,  # noqa: F401
            tasks,  # noqa: F401
        )

        # Register the system jobs (kept out of the tasks package __init__ to
        # avoid a circular import with coldfront.core.models).
        from .tasks import system  # noqa: F401

        # Register models
        register_models(*self.get_models())
