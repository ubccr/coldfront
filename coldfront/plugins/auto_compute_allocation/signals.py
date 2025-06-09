# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin signals.py"""

import logging

from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.project.signals import project_new
from coldfront.core.project.views import ProjectCreateView

logger = logging.getLogger(__name__)


@receiver(project_new, sender=ProjectCreateView)
def project_new_auto_compute_allocation(sender, **kwargs):
    project_obj = kwargs.get("project_obj")
    # Add a compute allocation
    async_task(
        "coldfront.plugins.auto_compute_allocation.tasks.add_auto_compute_allocation",
        project_obj,
    )
