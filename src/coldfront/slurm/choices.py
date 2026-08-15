# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.choices import ChoiceSet


class SlurmAdminLevelChoices(ChoiceSet):
    key = "slurm.SlurmUser.admin_level"

    LEVEL_NOTSET = 0
    LEVEL_NONE = 1
    LEVEL_OPERATOR = 2
    LEVEL_ADMIN = 3

    CHOICES = [
        (LEVEL_NOTSET, _("Not Set"), "secondary"),
        (LEVEL_NONE, _("None"), "info"),
        (LEVEL_OPERATOR, _("Operator"), "warning"),
        (LEVEL_ADMIN, _("Administrator"), "danger"),
    ]


class SlurmPartitionStateChoices(ChoiceSet):
    key = "slurm.SlurmPartition.state"

    STATE_UP = "UP"
    STATE_DOWN = "DOWN"
    STATE_DRAIN = "DRAIN"
    STATE_INACTIVE = "INACTIVE"

    CHOICES = [
        (STATE_UP, _("UP"), "success"),
        (STATE_DOWN, _("DOWN"), "danger"),
        (STATE_DRAIN, _("DRAIN"), "warning"),
        (STATE_INACTIVE, _("INACTIVE"), "secondary"),
    ]


class SlurmPreemptModeChoices(ChoiceSet):
    key = "slurm.SlurmPartition.preempt_mode"

    MODE_OFF = "OFF"
    MODE_SUSPEND = "SUSPEND"
    MODE_REQUEUE = "REQUEUE"
    MODE_CANCEL = "CANCEL"
    MODE_GANG = "GANG"
    MODE_WITHIN = "WITHIN"
    MODE_PRIORITY = "PRIORITY"

    CHOICES = [
        (MODE_OFF, _("OFF"), "secondary"),
        (MODE_SUSPEND, _("SUSPEND"), "info"),
        (MODE_REQUEUE, _("REQUEUE"), "warning"),
        (MODE_CANCEL, _("CANCEL"), "danger"),
        (MODE_GANG, _("GANG"), "primary"),
        (MODE_WITHIN, _("WITHIN"), "info"),
        (MODE_PRIORITY, _("PRIORITY"), "warning"),
    ]
