# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    AllocatableResourceBulkEditForm,
    OrganizationalModelBulkEditForm,
    PrimaryModelBulkEditForm,
)
from coldfront.forms.fields import JSONField
from coldfront.forms.widgets import BulkEditNullBooleanSelect
from coldfront.slurm.choices import (
    SlurmAdminLevelChoices,
    SlurmPartitionStateChoices,
    SlurmPreemptModeChoices,
)
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmPartition, SlurmQOS, SlurmUser
from coldfront.users.models.users import Group

#
# Slurm QOS
#


class SlurmQOSBulkEditForm(OrganizationalModelBulkEditForm):
    priority = forms.IntegerField(
        required=False,
        label=_("Priority"),
    )
    max_submit_jobs_per_user = forms.IntegerField(
        required=False,
        label=_("Max Submit Jobs per User"),
    )
    max_jobs_per_user = forms.IntegerField(
        required=False,
        label=_("Max Jobs per User"),
    )
    max_submit_jobs_per_account = forms.IntegerField(
        required=False,
        label=_("Max Submit Jobs per Account"),
    )
    max_jobs_per_account = forms.IntegerField(
        required=False,
        label=_("Max Jobs per Account"),
    )
    max_wall_duration_per_job = forms.IntegerField(
        required=False,
        label=_("Max Wall Duration per Job (minutes)"),
        help_text=_("Duration in minutes"),
    )
    limit_factor = forms.FloatField(
        required=False,
        label=_("Limit Factor"),
    )
    grace_time = forms.IntegerField(
        required=False,
        label=_("Grace Time (seconds)"),
    )

    model = SlurmQOS
    nullable_fields = (
        "description",
        "priority",
        "max_submit_jobs_per_user",
        "max_jobs_per_user",
        "max_submit_jobs_per_account",
        "max_jobs_per_account",
        "max_wall_duration_per_job",
        "limit_factor",
        "grace_time",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm QOS"),
                "description",
            ),
            Fieldset(
                _("Limits"),
                "priority",
                "max_submit_jobs_per_user",
                "max_jobs_per_user",
                "max_submit_jobs_per_account",
                "max_jobs_per_account",
                "max_wall_duration_per_job",
                "limit_factor",
                "grace_time",
            ),
        ]


#
# Slurm clusters
#


class SlurmClusterBulkEditForm(AllocatableResourceBulkEditForm, PrimaryModelBulkEditForm):
    default_qos = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
    )
    qos_list = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS List"),
    )
    fairshare = forms.IntegerField(
        required=False,
        label=_("Fairshare"),
    )
    features = JSONField(
        label=_("Features"),
        required=False,
        help_text=_(
            'Cluster features (GPU types, etc.) as a JSON array (e.g., ["gpu","highmem"]). '
            "Used to describe federated cluster capabilities. "
            "When submitting a federated job, --features filters which "
            "cluster receives the job based on these values."
        ),
    )
    classification = forms.CharField(
        max_length=50,
        required=False,
        label=_("Classification"),
    )

    model = SlurmCluster
    nullable_fields = (
        "tenant_group",
        "tenant",
        "description",
        "locked",
        "schema",
        "default_qos",
        "qos_list",
        "fairshare",
        "features",
        "classification",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm Cluster"),
                "description",
                "locked",
                "schema",
            ),
            Fieldset(
                _("Slurm Accounting"),
                "default_qos",
                "qos_list",
                "fairshare",
                "features",
                "classification",
            ),
        ]


#
# Slurm partitions
#


class SlurmPartitionBulkEditForm(AllocatableResourceBulkEditForm, PrimaryModelBulkEditForm):
    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    nodes = forms.CharField(
        max_length=255,
        required=False,
        label=_("Nodes"),
    )
    priority = forms.IntegerField(
        required=False,
        label=_("Priority"),
    )
    locked = forms.NullBooleanField(
        label=_("Locked"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )
    is_default = forms.NullBooleanField(
        label=_("Default"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )
    default_time = forms.IntegerField(
        required=False,
        label=_("Default Time (minutes)"),
        help_text=_("Duration in minutes"),
    )
    state = forms.ChoiceField(
        required=False,
        label=_("State"),
        choices=SlurmPartitionStateChoices,
    )
    preempt_mode = forms.ChoiceField(
        required=False,
        label=_("Preempt Mode"),
        choices=SlurmPreemptModeChoices,
    )
    def_mem_per_cpu = forms.IntegerField(
        required=False,
        label=_("Default Memory per CPU"),
    )
    max_jobs = forms.IntegerField(
        required=False,
        label=_("Max Jobs"),
    )
    max_submit_jobs = forms.IntegerField(
        required=False,
        label=_("Max Submit Jobs"),
    )
    max_tres_per_job = JSONField(
        label=_("Max TRES per Job"),
        required=False,
        help_text=_('JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).'),
    )
    max_tres_per_node = JSONField(
        label=_("Max TRES per Node"),
        required=False,
        help_text=_('JSON dict of TRES limits per node (e.g., {"gpu":8}).'),
    )
    max_tres_mins_per_job = JSONField(
        label=_("Max TRES Minutes per Job"),
        required=False,
        help_text=_('JSON dict of TRES minute limits per job (e.g., {"cpu":360}).'),
    )
    max_wall_duration_per_job = forms.IntegerField(
        required=False,
        label=_("Max Wall Duration per Job (minutes)"),
        help_text=_("Duration in minutes"),
    )
    fairshare = forms.IntegerField(
        required=False,
        label=_("Fairshare"),
    )
    allow_qos = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Allowed QOS"),
        help_text=_(
            "QOS whitelist for admission control. Only jobs requesting one of "
            "these QOSes are permitted to submit to this partition. "
            "Maps to AllowQOS in slurm.conf."
        ),
    )
    qos = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS"),
        help_text=_(
            "Partition-level QOS whose resource limits (max time, CPUs, "
            "memory) apply to every job in this partition. The partition "
            "QOS and the job's QOS are both enforced — the stricter limit "
            "wins. Maps to QOS in slurm.conf."
        ),
    )
    allow_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Allowed Groups"),
        help_text=_(
            "Restrict partition access to specific ColdFront Groups. Users "
            "must be in one of these groups to submit allocations to this "
            "partition. Maps to AllowGroups in slurm.conf."
        ),
    )
    allow_accounts = forms.ModelMultipleChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Allowed Accounts"),
        help_text=_(
            "Restrict which SlurmAccounts can submit jobs to this partition. "
            "When set, only associations under one of these accounts are permitted."
        ),
    )

    model = SlurmPartition
    nullable_fields = (
        "description",
        "locked",
        "schema",
        "nodes",
        "priority",
        "is_default",
        "default_time",
        "state",
        "preempt_mode",
        "def_mem_per_cpu",
        "max_jobs",
        "max_submit_jobs",
        "max_tres_per_job",
        "max_tres_per_node",
        "max_tres_mins_per_job",
        "max_wall_duration_per_job",
        "fairshare",
        "allow_qos",
        "qos",
        "allow_groups",
        "allow_accounts",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm Partition"),
                "cluster",
                "description",
                "locked",
                "schema",
                "nodes",
                "priority",
                "is_default",
                "default_time",
                "state",
                "preempt_mode",
                "def_mem_per_cpu",
            ),
            Fieldset(
                _("Limits"),
                "max_jobs",
                "max_submit_jobs",
                "max_tres_per_job",
                "max_tres_per_node",
                "max_tres_mins_per_job",
                "max_wall_duration_per_job",
                "fairshare",
            ),
            Fieldset(
                _("Access Control"),
                "allow_qos",
                "qos",
                "allow_groups",
                "allow_accounts",
            ),
        ]


#
# Slurm accounts
#


class SlurmAccountBulkEditForm(PrimaryModelBulkEditForm):
    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    fairshare = forms.IntegerField(
        required=False,
        label=_("Fairshare"),
    )
    qos_add = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS Add"),
    )
    qos_remove = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS Remove"),
    )

    model = SlurmAccount
    nullable_fields = ("description", "fairshare", "qos_add", "qos_remove")

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm Account"),
                "cluster",
                "description",
                "fairshare",
                "qos_add",
                "qos_remove",
            ),
        ]


#
# Slurm associations
#


class SlurmAssociationBulkEditForm(PrimaryModelBulkEditForm):
    slurm_account = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Slurm Account"),
    )
    parent = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Parent Account"),
    )
    default_qos = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
    )
    fairshare = forms.IntegerField(
        required=False,
        label=_("Fairshare"),
    )
    max_jobs = forms.IntegerField(
        required=False,
        label=_("Max Jobs"),
    )
    max_submit_jobs = forms.IntegerField(
        required=False,
        label=_("Max Submit Jobs"),
    )
    max_tres_per_job = JSONField(
        label=_("Max TRES per Job"),
        required=False,
        help_text=_('JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).'),
    )
    max_tres_mins_per_job = JSONField(
        label=_("Max TRES Minutes per Job"),
        required=False,
        help_text=_('JSON dict of TRES minute limits per job (e.g., {"cpu":360}).'),
    )
    max_wall_duration_per_job = forms.IntegerField(
        required=False,
        label=_("Max Wall Duration per Job (minutes)"),
        help_text=_("Duration in minutes"),
    )
    qos_add = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS Add"),
        help_text=_(
            "QOSes to add to this association via QOS+= in the dump format. "
            "These are added on top of the cluster/account defaults."
        ),
    )
    qos_remove = forms.ModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS Remove"),
        help_text=_(
            "QOSes to remove from this association via QOS-= in the dump format. "
            "These are subtracted from the inherited QOS list."
        ),
    )

    model = SlurmAssociation
    nullable_fields = (
        "description",
        "slurm_account",
        "parent",
        "default_qos",
        "fairshare",
        "max_jobs",
        "max_submit_jobs",
        "max_tres_per_job",
        "max_tres_mins_per_job",
        "max_wall_duration_per_job",
        "qos_add",
        "qos_remove",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm Association"),
                "slurm_account",
                "parent",
                "default_qos",
                "fairshare",
            ),
            Fieldset(
                _("Limits"),
                "max_jobs",
                "max_submit_jobs",
                "max_tres_per_job",
                "max_tres_mins_per_job",
                "max_wall_duration_per_job",
            ),
            Fieldset(
                _("QOS Configuration"),
                "qos_add",
                "qos_remove",
            ),
        ]


#
# Slurm users
#


class SlurmUserBulkEditForm(PrimaryModelBulkEditForm):
    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
        help_text=_("The Slurm cluster this user record lives on. One record per (user, cluster) pair."),
    )
    default_account = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Default Account"),
        help_text=_(
            "User's default Slurm account on this cluster. Jobs submitted "
            "by this user without specifying an account use this."
        ),
    )
    default_wckey = forms.CharField(
        max_length=100,
        required=False,
        label=_("Default WCKey"),
        help_text=_("Default wckey for fairshare and accounting."),
    )
    default_qos = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
        help_text=_("Default QOS for this user on this cluster. Applies to all jobs regardless of association."),
    )
    admin_level = forms.ChoiceField(
        required=False,
        label=_("Admin Level"),
        choices=SlurmAdminLevelChoices,
        help_text=_(
            "Slurm administrator level for this user. Not Set (0), None (1), "
            "Operator (2), or Administrator (3). Operators can modify "
            "accounting entities; Administrators have full control."
        ),
    )

    model = SlurmUser
    nullable_fields = ("description", "default_wckey", "default_qos", "admin_level")

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Slurm User"),
                "cluster",
                "default_account",
                "default_wckey",
                "default_qos",
                "admin_level",
            ),
        ]
