# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now
from django.core.validators import MaxValueValidator, MinValueValidator

from simple_history.models import HistoricalRecords


class MaintenanceEvent(models.Model):
    """Describes a maintenance window

    Attributes:
        start_time: start time for the maintenance
        end_time: end time for the maintenance
        stop_tasks: true/false pause tasks
        is_stopped: true/false to indicate if tasks are stopped
        extension: (int) number of days to extend impacted allocations
        message: text to display during maintenance
    """

    start_time = models.DateTimeField(null=False, blank=False)
    end_time = models.DateTimeField(null=False, blank=False)
    stop_tasks = models.BooleanField(default=False)
    is_stopped = models.BooleanField(default=False)
    extension = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(14), MinValueValidator(0)])
    message = models.TextField()
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(start_time__lte=F("end_time")), name="datetime_consistency"),
        ]
