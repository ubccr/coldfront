# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django_q.models import Schedule

from coldfront.core.allocation.models import Allocation
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.maintenance_mode.models import MaintenanceEvent

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_maintenance_state(ignore_cache=False):
    cache_status_label = "maintenence_mode_status"
    cache_message_label = "maintenence_mode_message"
    if ignore_cache:
        message = None
        status = None
    else:
        message = cache.get(cache_message_label)
        status = cache.get(cache_status_label)

    if not message or not status:
        current_time = datetime.now()
        maintenance_events = MaintenanceEvent.objects.filter(start_time__lte=current_time, end_time__gte=current_time)
        if maintenance_events.exists():
            message = maintenance_events.first().message
            status = True
        else:
            message = ""
            status = False

        cache.set(cache_message_label, message, 5 * 60)  # 5 minutes
        cache.set(cache_status_label, status, 5 * 60)  # 5 minutes

    return status, message


def pause_tasks(maintenance_obj):
    # only pause if the maintenance object has that property
    # and they're not already paused
    if maintenance_obj.stop_tasks and not maintenance_obj.is_stopped:
        MAINTENANCE_TASK_LOG_DIR = import_from_settings("MAINTENANCE_TASK_LOG_DIR")
        MAINTENANCE_EXCLUDED_TASK_IDS = import_from_settings("MAINTENANCE_EXCLUDED_TASK_IDS")

        enable_output = False
        if MAINTENANCE_TASK_LOG_DIR != "":
            log_dir = Path(MAINTENANCE_TASK_LOG_DIR)
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                enable_output = True
            except Exception as e:
                logger.error(
                    "Failed to ensure log directory {} exists with error {}".format(MAINTENANCE_TASK_LOG_DIR, e)
                )

        if not enable_output:
            logger.warning(
                "Output is not enabled. It may not be possible to restore all tasks to their original state."
            )

        # get all tasks except for the maintenance checking task
        all_schedules = Schedule.objects.exclude(name="maintenance_mode_checker")

        task_dict = {}
        for task in all_schedules:
            if task.id in MAINTENANCE_EXCLUDED_TASK_IDS:
                continue
            task_dict[str(task.id)] = {}
            task_dict[str(task.id)]["repeats"] = task.repeats

            # setting repeat to 0 pauses tasks
            task.repeats = 0
            task.save()

        maintenance_obj.is_stopped = True
        maintenance_obj.save()

        if enable_output:
            output_file = log_dir.joinpath("task_log_{}.json".format(maintenance_obj.pk))
            try:
                with open(output_file, "w", encoding="utf-8") as json_file:
                    json.dump(task_dict, json_file, ensure_ascii=False, indent=2)
            except Exception:
                logger.error("Error writing task log to file: {e}")


def resume_tasks(maintenance_obj):
    # only resume if the maintenance object has that property
    # and they're paused
    if maintenance_obj.stop_tasks and maintenance_obj.is_stopped:
        MAINTENANCE_TASK_LOG_DIR = import_from_settings("MAINTENANCE_TASK_LOG_DIR")
        MAINTENANCE_EXCLUDED_TASK_IDS = import_from_settings("MAINTENANCE_EXCLUDED_TASK_IDS")

        read_log = False
        task_dict = {}
        if MAINTENANCE_TASK_LOG_DIR != "":
            log_dir = Path(MAINTENANCE_TASK_LOG_DIR)
            log_file = log_dir.joinpath("task_log_{}.json".format(maintenance_obj.pk))
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        task_dict = json.load(f)
                    read_log = True
                except Exception as e:
                    logger.error("Failed to read task log file: {}".format(e))

        if not read_log:
            logger.warning("Task log was not read. Tasks may not be restored to their original state.")

        # get all tasks except for the maintenance checking task
        all_schedules = Schedule.objects.exclude(name="maintenance_mode_checker")

        for task in all_schedules:
            if task.id in MAINTENANCE_EXCLUDED_TASK_IDS:
                continue

            if read_log:
                task.repeats = task_dict[str(task.id)]["repeats"]
                task.save()
            elif task.repeats == 0:
                # assume the task was running before if set to 0
                task.repeats = -1
                task.save()

        maintenance_obj.is_stopped = False
        maintenance_obj.save()


def extend_allocations(maintenance_obj):
    # only resume if the maintenance object has an extension
    if maintenance_obj.extension > 0:
        MAINTENANCE_ALLOCATION_IMPACT_PADDING = import_from_settings("MAINTENANCE_ALLOCATION_IMPACT_PADDING")

        check_start = maintenance_obj.start_time
        check_end = maintenance_obj.start_time + relativedelta(days=MAINTENANCE_ALLOCATION_IMPACT_PADDING)

        impacted_allocations = Allocation.objects.filter(end_date__gte=check_start, end_date__lte=check_end)

        for allocation_obj in impacted_allocations:
            allocation_obj.end_date = allocation_obj.end_date + relativedelta(days=maintenance_obj.extension)
            allocation_obj.save()
