# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime

from coldfront.plugins.maintenance_mode.models import MaintenanceEvent
from coldfront.plugins.maintenance_mode.utils import (
    extend_allocations,
    get_maintenance_state,
    pause_tasks,
    resume_tasks,
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


def check_maintenance():
    # check to see if there's active maintenance
    status, message = get_maintenance_state(True)

    if status:
        # get the maintenance object
        current_time = datetime.now()
        maintenance_events = MaintenanceEvent.objects.filter(
            start_time__lte=current_time, end_time__gte=current_time, message=message
        )

        if maintenance_events.exists():
            maintenance_obj = maintenance_events.first()

            if maintenance_obj.stop_tasks and not maintenance_obj.is_stopped:
                pause_tasks(maintenance_obj)
                extend_allocations(maintenance_obj)
        else:
            logger.error("Could not find a valid maintenance event")
    else:
        # there is no current maintenance. Check if there are paused tasks
        # from previous maintenance
        current_time = datetime.now()
        maintenance_events = MaintenanceEvent.objects.filter(
            end_time__lte=current_time, stop_tasks=True, is_stopped=True
        )

        if maintenance_events.exists():
            resume_tasks(maintenance_events.first())
