# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import PrimaryModelForm, PrimaryModelImportForm, TenancyForm, TenancyImportForm
from coldfront.forms.fields import (
    CSVChoiceField,
    CSVModelChoiceField,
    CSVModelMultipleChoiceField,
    CSVMultipleChoiceField,
    JSONField,
)
from coldfront.forms.layout import FieldSet
from coldfront.slurm.choices import (
    SlurmPriorityFlagsChoices,
    SlurmPriorityTypeChoices,
    SlurmPriorityUsageResetPeriodChoices,
)
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmPartition, SlurmQOS, SlurmUser
from coldfront.utils.forms import add_blank_choice


class SlurmQOSForm(PrimaryModelForm):
    class Meta:
        model = SlurmQOS
        fields = [
            "name",
            "description",
            "priority",
            "max_submit_jobs_per_user",
            "max_jobs_per_user",
            "max_submit_jobs_per_account",
            "max_jobs_per_account",
            "max_wall_duration_per_job",
            "limit_factor",
            "grace_time",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "name",
                "description",
                name=_("Slurm QOS"),
            ),
            FieldSet(
                "priority",
                "max_submit_jobs_per_user",
                "max_jobs_per_user",
                "max_submit_jobs_per_account",
                "max_jobs_per_account",
                "max_wall_duration_per_job",
                "limit_factor",
                "grace_time",
                name=_("Limits"),
            ),
        ]


class SlurmQOSImportForm(PrimaryModelImportForm):
    class Meta:
        model = SlurmQOS
        fields = [
            "name",
            "description",
            "priority",
            "max_submit_jobs_per_user",
            "max_jobs_per_user",
            "max_submit_jobs_per_account",
            "max_jobs_per_account",
            "max_wall_duration_per_job",
            "limit_factor",
            "grace_time",
            "tags",
        ]


class SlurmClusterForm(TenancyForm, PrimaryModelForm):
    schema = JSONField(
        label=_("Schema"),
        required=False,
        help_text=_("Enter a valid JSON schema to define supported allocation attributes."),
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

    priority_flags = forms.MultipleChoiceField(
        choices=add_blank_choice(SlurmPriorityFlagsChoices),
        required=False,
        label=_("Priority Flags"),
        help_text=_("Raw PriorityFlags from slurm.conf. Used to derive billing_mode (MAX_TRES / MAX_TRES_GRES)."),
    )

    class Meta:
        model = SlurmCluster
        fields = [
            "name",
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
            "priority_flags",
            "priority_type",
            "priority_decay_half_life",
            "priority_usage_reset_period",
            "enforce_su_limits",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "name",
                "description",
                "locked",
                "schema",
                name=_("Slurm Cluster"),
            ),
            FieldSet(
                "default_qos",
                "qos_list",
                "fairshare",
                "features",
                "classification",
                name=_("Slurm Accounting"),
            ),
            FieldSet(
                "priority_flags",
                "priority_type",
                "priority_decay_half_life",
                "priority_usage_reset_period",
                "enforce_su_limits",
                name=_("Billing & Enforcement"),
            ),
        ]


class SlurmClusterImportForm(TenancyImportForm, PrimaryModelImportForm):
    default_qos = CSVModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Default QOS"),
    )

    priority_flags = CSVMultipleChoiceField(
        choices=SlurmPriorityFlagsChoices,
        required=False,
        label=_("Priority Flags"),
    )

    priority_type = CSVChoiceField(
        choices=SlurmPriorityTypeChoices,
        required=False,
        label=_("Priority Type"),
    )

    priority_decay_half_life = forms.CharField(
        required=False,
        label=_("Priority Decay Half Life"),
    )

    priority_usage_reset_period = CSVChoiceField(
        choices=SlurmPriorityUsageResetPeriodChoices,
        required=False,
        label=_("Priority Usage Reset Period"),
    )

    class Meta:
        model = SlurmCluster
        fields = [
            "name",
            "tenant",
            "description",
            "locked",
            "schema",
            "default_qos",
            "fairshare",
            "features",
            "classification",
            "priority_flags",
            "priority_type",
            "priority_decay_half_life",
            "priority_usage_reset_period",
            "tags",
        ]


class SlurmPartitionForm(PrimaryModelForm):
    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        label=_("Cluster"),
    )

    schema = JSONField(
        label=_("Schema"),
        required=False,
        help_text=_("Enter a valid JSON schema to define supported allocation attributes."),
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

    class Meta:
        model = SlurmPartition
        fields = [
            "cluster",
            "name",
            "slug",
            "description",
            "locked",
            "schema",
            "nodes",
            "priority",
            "priority_tier",
            "max_nodes",
            "max_cpus_per_node",
            "is_default",
            "default_time",
            "state",
            "preempt_mode",
            "def_mem_per_cpu",
            "def_mem_per_node",
            "max_time",
            "tres_billing_weights",
            "allow_qos",
            "deny_qos",
            "qos",
            "allow_groups",
            "allow_accounts",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "cluster",
                "name",
                "slug",
                "description",
                "locked",
                "schema",
                "nodes",
                "priority",
                "priority_tier",
                "max_nodes",
                "max_cpus_per_node",
                "is_default",
                "default_time",
                "state",
                "preempt_mode",
                "def_mem_per_cpu",
                "def_mem_per_node",
                name=_("Slurm Partition"),
            ),
            FieldSet(
                "max_time",
                "tres_billing_weights",
                name=_("Limits"),
            ),
            FieldSet(
                "allow_qos",
                "deny_qos",
                "qos",
                "allow_groups",
                "allow_accounts",
                name=_("Access Control"),
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass


class SlurmPartitionImportForm(PrimaryModelImportForm):
    cluster = CSVModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        to_field_name="name",
        label=_("Cluster"),
    )

    class Meta:
        model = SlurmPartition
        fields = [
            "cluster",
            "name",
            "slug",
            "description",
            "locked",
            "schema",
            "nodes",
            "priority",
            "priority_tier",
            "max_nodes",
            "max_cpus_per_node",
            "is_default",
            "default_time",
            "state",
            "preempt_mode",
            "def_mem_per_cpu",
            "def_mem_per_node",
            "max_time",
            "tres_billing_weights",
            "tags",
        ]


class SlurmAccountForm(PrimaryModelForm):
    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        label=_("Cluster"),
    )

    class Meta:
        model = SlurmAccount
        fields = [
            "cluster",
            "name",
            "description",
            "fairshare",
            "service_units",
            "qos_add",
            "qos_remove",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "cluster",
                "name",
                "description",
                "fairshare",
                "service_units",
                "qos_add",
                "qos_remove",
                name=_("Slurm Account"),
            ),
        ]


class SlurmAccountImportForm(PrimaryModelImportForm):
    cluster = CSVModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        to_field_name="name",
        label=_("Cluster"),
    )

    class Meta:
        model = SlurmAccount
        fields = [
            "cluster",
            "name",
            "description",
            "fairshare",
            "qos_add",
            "qos_remove",
            "tags",
        ]


class SlurmAssociationForm(PrimaryModelForm):
    allocation = forms.ModelChoiceField(
        queryset=SlurmAssociation.objects.all(),  # placeholder, will override __init__
        label=_("Allocation"),
    )

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

    max_tres_per_job = JSONField(
        label=_("Max TRES per Job"),
        required=False,
        help_text=_('JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).'),
    )

    max_tres_mins_per_job = JSONField(
        label=_("Max TRES minutes per job"),
        required=False,
        help_text=_('JSON dict of TRES minute limits per job (e.g., {"cpu":360}).'),
    )

    class Meta:
        model = SlurmAssociation
        fields = [
            "allocation",
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
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "allocation",
                "slurm_account",
                "parent",
                "default_qos",
                "fairshare",
                name=_("Slurm Association"),
            ),
            FieldSet(
                "max_jobs",
                "max_submit_jobs",
                "max_tres_per_job",
                "max_tres_mins_per_job",
                "max_wall_duration_per_job",
                name=_("Limits"),
            ),
            FieldSet(
                "qos_add",
                "qos_remove",
                name=_("QOS Configuration"),
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.ras.models import Allocation

        self.fields["allocation"] = forms.ModelChoiceField(
            queryset=Allocation.objects.all(),
            label=_("Allocation"),
        )


class SlurmAssociationImportForm(PrimaryModelImportForm):
    allocation = CSVModelChoiceField(
        queryset=SlurmAssociation.objects.all(),  # placeholder, will override __init__
        to_field_name="slug",
        label=_("Allocation"),
    )

    slurm_account = CSVModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Slurm Account"),
    )

    parent = CSVModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Parent Account"),
    )

    default_qos = CSVModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Default QOS"),
    )

    qos_add = CSVModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        to_field_name="name",
        required=False,
        label=_("QOS Add"),
    )
    qos_remove = CSVModelMultipleChoiceField(
        queryset=SlurmQOS.objects.all(),
        to_field_name="name",
        required=False,
        label=_("QOS Remove"),
    )

    class Meta:
        model = SlurmAssociation
        fields = [
            "allocation",
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
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.ras.models import Allocation

        self.fields["allocation"] = CSVModelChoiceField(
            queryset=Allocation.objects.all(),
            to_field_name="slug",
            label=_("Allocation"),
        )


class SlurmUserForm(PrimaryModelForm):
    user = forms.ModelChoiceField(
        queryset=SlurmUser.objects.all(),  # placeholder, will override __init__
        label=_("User"),
        help_text=_("The ColdFront user this Slurm user record represents."),
    )

    cluster = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        label=_("Cluster"),
        help_text=_("The Slurm cluster this user record lives on. One record per (user, cluster) pair."),
    )

    default_account = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        label=_("Default Account"),
        help_text=_(
            "User's default Slurm account on this cluster. Jobs submitted "
            "by this user without specifying an account use this."
        ),
    )

    default_qos = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
        help_text=_("Default QOS for this user on this cluster. Applies to all jobs regardless of association."),
    )

    class Meta:
        model = SlurmUser
        fields = [
            "user",
            "cluster",
            "default_account",
            "default_wckey",
            "default_qos",
            "admin_level",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "user",
                "cluster",
                "default_account",
                "default_wckey",
                "default_qos",
                "admin_level",
                name=_("Slurm User"),
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.users.models import User

        self.fields["user"] = forms.ModelChoiceField(
            queryset=User.objects.all(),
            label=_("User"),
        )


class SlurmUserImportForm(PrimaryModelImportForm):
    user = CSVModelChoiceField(
        queryset=SlurmUser.objects.none(),  # placeholder, will override __init__
        to_field_name="username",
        label=_("User"),
    )

    cluster = CSVModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        to_field_name="name",
        label=_("Cluster"),
    )

    default_account = CSVModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        to_field_name="name",
        label=_("Default Account"),
    )

    default_qos = CSVModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Default QOS"),
    )

    class Meta:
        model = SlurmUser
        fields = [
            "user",
            "cluster",
            "default_account",
            "default_wckey",
            "default_qos",
            "admin_level",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.users.models import User

        self.fields["user"] = CSVModelChoiceField(
            queryset=User.objects.all(),
            to_field_name="username",
            label=_("User"),
        )
