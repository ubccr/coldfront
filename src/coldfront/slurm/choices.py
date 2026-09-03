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


class SlurmPriorityFlagsChoices(ChoiceSet):
    """Allowed values for the global PriorityFlags setting in slurm.conf."""

    key = "slurm.SlurmCluster.priority_flags"

    FLAG_ACCRUE_ALWAYS = "ACCRUE_ALWAYS"
    FLAG_CALCULATE_RUNNING = "CALCULATE_RUNNING"
    FLAG_DEPTH_OBLIVIOUS = "DEPTH_OBLIVIOUS"
    FLAG_NO_FAIR_TREE = "NO_FAIR_TREE"
    FLAG_INCR_ONLY = "INCR_ONLY"
    FLAG_MAX_TRES = "MAX_TRES"
    FLAG_MAX_TRES_GRES = "MAX_TRES_GRES"
    FLAG_NO_NORMAL_ALL = "NO_NORMAL_ALL"
    FLAG_NO_NORMAL_ASSOC = "NO_NORMAL_ASSOC"
    FLAG_NO_NORMAL_PART = "NO_NORMAL_PART"
    FLAG_NO_NORMAL_QOS = "NO_NORMAL_QOS"
    FLAG_NO_NORMAL_TRES = "NO_NORMAL_TRES"
    FLAG_SMALL_RELATIVE_TO_TIME = "SMALL_RELATIVE_TO_TIME"

    CHOICES = [
        (FLAG_ACCRUE_ALWAYS, _("ACCRUE_ALWAYS"), "secondary"),
        (FLAG_CALCULATE_RUNNING, _("CALCULATE_RUNNING"), "info"),
        (FLAG_DEPTH_OBLIVIOUS, _("DEPTH_OBLIVIOUS"), "info"),
        (FLAG_NO_FAIR_TREE, _("NO_FAIR_TREE"), "secondary"),
        (FLAG_INCR_ONLY, _("INCR_ONLY"), "info"),
        (FLAG_MAX_TRES, _("MAX_TRES"), "warning"),
        (FLAG_MAX_TRES_GRES, _("MAX_TRES_GRES"), "danger"),
        (FLAG_NO_NORMAL_ALL, _("NO_NORMAL_ALL"), "secondary"),
        (FLAG_NO_NORMAL_ASSOC, _("NO_NORMAL_ASSOC"), "secondary"),
        (FLAG_NO_NORMAL_PART, _("NO_NORMAL_PART"), "secondary"),
        (FLAG_NO_NORMAL_QOS, _("NO_NORMAL_QOS"), "secondary"),
        (FLAG_NO_NORMAL_TRES, _("NO_NORMAL_TRES"), "secondary"),
        (FLAG_SMALL_RELATIVE_TO_TIME, _("SMALL_RELATIVE_TO_TIME"), "info"),
    ]


class SlurmPriorityTypeChoices(ChoiceSet):
    """Allowed values for the global PriorityType setting in slurm.conf."""

    key = "slurm.SlurmCluster.priority_type"

    PRIORITY_BASIC = "priority/basic"
    PRIORITY_MULTIFACTOR = "priority/multifactor"

    CHOICES = [
        (PRIORITY_BASIC, _("priority/basic"), "secondary"),
        (PRIORITY_MULTIFACTOR, _("priority/multifactor"), "primary"),
    ]


class SlurmPriorityUsageResetPeriodChoices(ChoiceSet):
    """Allowed values for the global PriorityUsageResetPeriod setting in slurm.conf."""

    key = "slurm.SlurmCluster.priority_usage_reset_period"

    PERIOD_NONE = "NONE"
    PERIOD_NOW = "NOW"
    PERIOD_DAILY = "DAILY"
    PERIOD_WEEKLY = "WEEKLY"
    PERIOD_MONTHLY = "MONTHLY"
    PERIOD_QUARTERLY = "QUARTERLY"
    PERIOD_YEARLY = "YEARLY"

    CHOICES = [
        (PERIOD_NONE, _("NONE"), "secondary"),
        (PERIOD_NOW, _("NOW"), "danger"),
        (PERIOD_DAILY, _("DAILY"), "info"),
        (PERIOD_WEEKLY, _("WEEKLY"), "info"),
        (PERIOD_MONTHLY, _("MONTHLY"), "warning"),
        (PERIOD_QUARTERLY, _("QUARTERLY"), "warning"),
        (PERIOD_YEARLY, _("YEARLY"), "danger"),
    ]


class SlurmBillingModeChoices(ChoiceSet):
    """ColdFront concept: how TRES are aggregated into billable SUs.

    Derived from SlurmCluster.priority_flags. Not a slurm.conf value.
    """

    key = "slurm.SlurmCluster.billing_mode"

    MODE_SUM = "sum"
    MODE_MAX_TRES = "max_tres"
    MODE_MAX_TRES_GRES = "max_tres_gres"

    CHOICES = [
        (MODE_SUM, _("Sum"), "info"),
        (MODE_MAX_TRES, _("Max TRES"), "warning"),
        (MODE_MAX_TRES_GRES, _("Max TRES GRES"), "danger"),
    ]


class SlurmSuEnforcementModeChoices(ChoiceSet):
    """ColdFront concept: how GrpTresMins usage is enforced by Slurm.

    Derived from priority_type, priority_decay_half_life and
    priority_usage_reset_period. Not a slurm.conf value.
    """

    key = "slurm.SlurmCluster.su_enforcement_mode"

    MODE_NONE = "none"
    MODE_DECAY = "decay"
    MODE_HARD = "hard"

    CHOICES = [
        (MODE_NONE, _("None"), "secondary"),
        (MODE_DECAY, _("Decay"), "warning"),
        (MODE_HARD, _("Hard"), "danger"),
    ]
