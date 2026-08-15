# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from coldfront.models import OrganizationalModel, PrimaryModel
from coldfront.models.features import AllocatableResourceMixin
from coldfront.ras.models.mixins import AllocationExtensionMixin
from coldfront.registry import register_allocation_extension
from coldfront.slurm.choices import (
    SlurmAdminLevelChoices,
    SlurmPartitionStateChoices,
    SlurmPreemptModeChoices,
)


class SlurmQOS(OrganizationalModel):
    """
    A model representing a Slurm Quality of Service profile.
    Referenced by SlurmPartition.allow_qos (M2M), SlurmCluster.qos_list (M2M),
    and SlurmAccount.qos_list (M2M).
    """

    priority = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("priority"),
        help_text=_(
            "QOS priority factor. Higher values increase a job's priority "
            "when this QOS is used. Maps to Priority in the dump format."
        ),
    )
    max_submit_jobs_per_user = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max submit jobs per user"),
        help_text=_(
            "Maximum number of jobs a user can submit with this QOS. Maps to MaxSubmitJobsPU in the dump format."
        ),
    )
    max_jobs_per_user = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max jobs per user"),
        help_text=_(
            "Maximum number of running jobs a user can have with this QOS. Maps to MaxJobsPU in the dump format."
        ),
    )
    max_submit_jobs_per_account = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max submit jobs per account"),
        help_text=_(
            "Maximum number of jobs an account can submit with this QOS. Maps to MaxSubmitJobsPA in the dump format."
        ),
    )
    max_jobs_per_account = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max jobs per account"),
        help_text=_(
            "Maximum number of running jobs an account can have with this QOS. Maps to MaxJobsPA in the dump format."
        ),
    )
    max_wall_duration_per_job = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_("max wall duration per job"),
        help_text=_(
            "Maximum wall clock time per job using this QOS. Maps to MaxWallDurationPerJob in the dump format."
        ),
    )
    limit_factor = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("limit factor"),
        help_text=_(
            "A float that is factored into an association's GrpTRES limits. Maps to LimitFactor in the dump format."
        ),
    )
    grace_time = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("grace time"),
        help_text=_(
            "Preemption grace time in seconds. Jobs selected for preemption "
            "are given this much time before termination. "
            "Maps to GraceTime in the dump format."
        ),
    )

    clone_fields = (
        "priority",
        "max_submit_jobs_per_user",
        "max_jobs_per_user",
        "max_submit_jobs_per_account",
        "max_jobs_per_account",
        "max_wall_duration_per_job",
        "limit_factor",
        "grace_time",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("slurm qos")
        verbose_name_plural = _("slurm qos")

    def get_status_color(self):
        return "green"


class SlurmCluster(AllocatableResourceMixin, PrimaryModel):
    """
    A Slurm cluster represents a compute cluster managed by the Slurm workload
    manager. It tracks the cluster name, its partitions, and custom attributes
    needed for generating Slurm association files or REST API calls.
    """

    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="slurm_clusters",
        blank=True,
        null=True,
    )

    default_qos = models.ForeignKey(
        to="slurm.SlurmQOS",
        on_delete=models.PROTECT,
        related_name="default_for_clusters",
        blank=True,
        null=True,
        verbose_name=_("default QOS"),
        help_text=_("Default QOS applied to jobs that do not specify one. Maps to DefaultQOS in the dump format"),
    )

    qos_list = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="clusters",
        related_query_name="cluster",
        verbose_name=_("QOS list"),
        help_text=_("QOS options available on this cluster. Associations inherit these via QOS+= syntax."),
    )

    fairshare = models.PositiveIntegerField(
        blank=True,
        default=1,
        verbose_name=_("fairshare"),
        help_text=_(
            "Default fairshare value for this cluster. Used as the root "
            "association's shares_raw. All associations under this cluster "
            "inherit unless overridden. Maps to Fairshare in the dump "
            "format."
        ),
    )

    features = models.JSONField(
        blank=True,
        null=True,
        default=list,
        verbose_name=_("features"),
        help_text=_(
            "Cluster features (GPU types, etc.) used to describe federated cluster capabilities. "
            "When submitting a federated job, --features filters which cluster receives the job."
        ),
    )

    classification = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("classification"),
        help_text=_("How this machine is classified."),
    )

    clone_fields = (
        "locked",
        "tenant",
        "default_qos",
        "qos_list",
        "fairshare",
        "features",
        "classification",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("slurm cluster")
        verbose_name_plural = _("slurm clusters")

    def __str__(self):
        return self.name

    def get_status_color(self):
        return "green"


class SlurmPartition(AllocatableResourceMixin, PrimaryModel):
    """
    A Slurm partition belongs to a SlurmCluster and represents a job
    submission queue within the cluster. Partitions have resource limits,
    node allocations, and scheduling policies that are needed for generating
    Slurm association data.
    """

    cluster = models.ForeignKey(
        to="slurm.SlurmCluster",
        on_delete=models.PROTECT,
        related_name="partitions",
        verbose_name=_("cluster"),
    )

    max_jobs = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max jobs"),
        help_text=_("Maximum number of jobs that can run simultaneously in this partition."),
    )

    max_submit_jobs = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max submit jobs"),
        help_text=_("Maximum number of jobs that can be submitted by this association."),
    )

    max_tres_per_job = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("max TRES per job"),
        help_text=_('JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).'),
    )

    max_tres_per_node = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("max TRES per node"),
        help_text=_('JSON dict of TRES limits per node (e.g., {"gpu":8}).'),
    )

    max_tres_mins_per_job = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("max TRES minutes per job"),
        help_text=_('JSON dict of TRES minute limits per job (e.g., {"cpu":360}).'),
    )

    max_wall_duration_per_job = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_("max wall duration per job"),
        help_text=_("Maximum wall clock duration per job."),
    )

    fairshare = models.PositiveIntegerField(
        blank=True,
        default=1,
        verbose_name=_("fairshare"),
        help_text=_(
            "Fairshare value for this partition's associations. Determines "
            "relative priority within the fairshare tree. Higher values "
            "allow more jobs before priority decays."
        ),
    )

    allow_qos = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="allowed_partitions",
        related_query_name="allowed_partition",
        verbose_name=_("allowed QOS"),
        help_text=_(
            "QOS whitelist for admission control. Only jobs requesting one "
            "of these QOSes are permitted to submit to this partition. "
            "Maps to AllowQOS in slurm.conf."
        ),
    )
    qos = models.ForeignKey(
        to="slurm.SlurmQOS",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="assigned_partitions",
        verbose_name=_("QOS"),
        help_text=_(
            "Partition-level QOS whose resource limits (max time, CPUs, "
            "memory) apply to every job in this partition. The partition "
            "QOS and the job's QOS are both enforced — the stricter limit "
            "wins. Maps to QOS in slurm.conf."
        ),
    )

    allow_groups = models.ManyToManyField(
        to="users.Group",
        blank=True,
        related_name="allowed_partitions",
        related_query_name="allowed_partition",
        verbose_name=_("allowed groups"),
        help_text=_(
            "Restrict partition access to specific ColdFront Groups. Users "
            "must be in one of these groups to submit allocations to this "
            "partition. Maps to AllowGroups in slurm.conf."
        ),
    )

    allow_accounts = models.ManyToManyField(
        to="slurm.SlurmAccount",
        blank=True,
        related_name="allowed_partitions",
        related_query_name="allowed_partition",
        verbose_name=_("allowed accounts"),
        help_text=_(
            "Restrict which SlurmAccounts can submit jobs to this partition. "
            "When set, only associations under one of these accounts are permitted."
        ),
    )

    nodes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("nodes"),
        help_text=_("Comma-separated node list for this partition (e.g., node[01-64])."),
    )

    priority = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("priority"),
        help_text=_("Priority tier for scheduling and preemption. Higher priority partitions are scheduled first."),
    )

    is_default = models.BooleanField(
        blank=True,
        default=False,
        verbose_name=_("default"),
        help_text=_("If set, this is the default partition for jobs that do not specify one."),
    )

    default_time = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_("default time"),
        help_text=_("Default job time limit for this partition."),
    )

    state = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("state"),
        choices=SlurmPartitionStateChoices,
        help_text=_("Partition state (UP, DOWN, DRAIN, INACTIVE)."),
    )

    preempt_mode = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("preempt mode"),
        choices=SlurmPreemptModeChoices,
        help_text=_("Preemption mode for this partition (e.g., OFF, SUSPEND, GANG, CANCEL)."),
    )

    def_mem_per_cpu = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("default memory per CPU"),
        help_text=_("Default memory per CPU in MB for jobs in this partition."),
    )

    slug = models.SlugField(
        verbose_name=_("slug"),
        max_length=100,
        blank=True,
        unique=True,
    )

    clone_fields = (
        "cluster",
        "locked",
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
        "nodes",
        "priority",
        "is_default",
        "default_time",
        "state",
        "preempt_mode",
        "def_mem_per_cpu",
        "slug",
    )

    prerequisite_models = ("slurm.SlurmCluster",)

    class Meta:
        ordering = ["cluster__name", "name"]
        verbose_name = _("slurm partition")
        verbose_name_plural = _("slurm partitions")
        constraints = (
            models.UniqueConstraint(
                fields=("cluster", "name"),
                name="%(app_label)s_%(class)s_unique_cluster_name",
            ),
        )

    def __str__(self):
        return f"{self.name} ({self.cluster.name})"

    def get_status_color(self):
        return "green"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.cluster.name}-{self.name}")
        super().save(*args, **kwargs)


class SlurmAccount(PrimaryModel):
    """
    A named Slurm accounting account, matching Slurm's acct_table.
    Accounts are lean containers (name, description, organization) --
    all per-association limits live on SlurmAssociation instead.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
    )

    cluster = models.ForeignKey(
        to="slurm.SlurmCluster",
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name=_("cluster"),
    )

    fairshare = models.PositiveIntegerField(
        blank=True,
        null=True,
        default=None,
        verbose_name=_("fairshare"),
        help_text=_(
            "Account-level fairshare. When set, all user associations "
            "under this account inherit via Fairshare=parent in the dump. "
        ),
    )

    qos_add = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="added_to_accounts",
        related_query_name="added_to_account",
        verbose_name=_("QOS add"),
        help_text=_(
            "QOSes to add to this account via QOS+= in the dump format. These are added on top of the cluster defaults."
        ),
    )
    qos_remove = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="removed_from_accounts",
        related_query_name="removed_from_account",
        verbose_name=_("QOS remove"),
        help_text=_(
            "QOSes to remove from this account via QOS-= in the dump format. "
            "These are subtracted from the inherited QOS list."
        ),
    )

    clone_fields = (
        "cluster",
        "fairshare",
        "qos_add",
        "qos_remove",
    )

    prerequisite_models = ("slurm.SlurmCluster",)

    class Meta:
        ordering = ["cluster__name", "name"]
        verbose_name = _("slurm account")
        verbose_name_plural = _("slurm accounts")
        constraints = (
            models.UniqueConstraint(
                fields=("cluster", "name"),
                name="%(app_label)s_%(class)s_unique_cluster_name",
            ),
        )

    def __str__(self):
        return f"{self.name} ({self.cluster.name})"

    def get_status_color(self):
        return "green"


@register_allocation_extension(SlurmCluster)
@register_allocation_extension(SlurmPartition)
class SlurmAssociation(AllocationExtensionMixin, PrimaryModel):
    """
    Carries resource-specific association data for an allocation on a
    ``SlurmCluster`` or ``SlurmPartition``.  Created when the allocation is
    created, and updated via change requests.

    Each (cluster, account, user, partition) row carries its own limits,
    fairshare, and hierarchy.
    """

    _requestable_fields = ["fairshare", "max_jobs", "max_submit_jobs", "max_wall_duration_per_job"]

    class Meta:
        ordering = ["allocation__slug"]
        verbose_name = _("slurm association")
        verbose_name_plural = _("slurm associations")

    slurm_account = models.ForeignKey(
        to="slurm.SlurmAccount",
        on_delete=models.PROTECT,
        related_name="associations",
        blank=True,
        null=True,
        verbose_name=_("Slurm account"),
        help_text=_("The Slurm account for this allocation. Links the allocation to a named Slurm accounting account."),
    )

    parent = models.ForeignKey(
        to="slurm.SlurmAccount",
        on_delete=models.PROTECT,
        related_name="child_associations",
        blank=True,
        null=True,
        verbose_name=_("parent account"),
        help_text=_("Parent account in the Slurm hierarchy for this association."),
    )

    default_qos = models.ForeignKey(
        to="slurm.SlurmQOS",
        on_delete=models.PROTECT,
        related_name="associations",
        blank=True,
        null=True,
        verbose_name=_("default QOS"),
        help_text=_(
            "Default QOS for this association. Jobs under this association inherit this QOS unless they specify one."
        ),
    )

    fairshare = models.PositiveIntegerField(
        blank=True,
        default=1,
        verbose_name=_("fairshare"),
        help_text=_("Fairshare value for this association. Determines relative priority within the fairshare tree."),
    )

    max_jobs = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max jobs"),
        help_text=_("Maximum number of jobs that can run simultaneously in this association."),
    )

    max_submit_jobs = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("max submit jobs"),
        help_text=_("Maximum number of jobs that can be submitted by this association."),
    )

    max_tres_per_job = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("max TRES per job"),
        help_text=_('JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).'),
    )

    max_tres_mins_per_job = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("max TRES minutes per job"),
        help_text=_('JSON dict of TRES minute limits per job (e.g., {"cpu":360}).'),
    )

    max_wall_duration_per_job = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_("max wall duration per job"),
        help_text=_("Maximum wall clock duration per job."),
    )

    qos_add = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="added_to_associations",
        related_query_name="added_to_association",
        verbose_name=_("QOS add"),
        help_text=_(
            "QOSes to add to this association via QOS+= in the dump format. "
            "These are added on top of the cluster/account defaults."
        ),
    )
    qos_remove = models.ManyToManyField(
        to="slurm.SlurmQOS",
        blank=True,
        related_name="removed_from_associations",
        related_query_name="removed_from_association",
        verbose_name=_("QOS remove"),
        help_text=_(
            "QOSes to remove from this association via QOS-= in the dump format. "
            "These are subtracted from the inherited QOS list."
        ),
    )

    def clean(self):
        """
        Validate that the slurm_account does not create duplicate
        (user, acct, partition) tuples in the Slurm dump.

        Raises ValidationError if another SlurmAssociation with the same
        slurm_account targets the same resource scope:
          - Same SlurmCluster directly (partition='')
          - Same SlurmPartition (partition='<name>')
        """
        super().clean()
        if self.slurm_account is None:
            return

        allocation = self.allocation
        if allocation is None:
            return
        resource = allocation.resource_object
        if resource is None:
            return

        # Query other associations with the same slurm_account, excluding self
        qs = SlurmAssociation.objects.filter(slurm_account=self.slurm_account)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if isinstance(resource, SlurmCluster):
            # Direct-to-cluster: check no other association targets the same
            # cluster directly with the same account
            cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
            for other in qs.select_related("allocation"):
                other_alloc = other.allocation
                if (
                    other_alloc.resource_object_type_id == cluster_ct.pk
                    and other_alloc.resource_object_id == resource.pk
                ):
                    raise ValidationError(
                        _(
                            "Another association already uses account "
                            "'%(account)s' for a direct allocation on "
                            "cluster '%(cluster)s'."
                        )
                        % {
                            "account": self.slurm_account.name,
                            "cluster": resource.name,
                        }
                    )

        elif isinstance(resource, SlurmPartition):
            # Partition-specific: check no other association targets the same
            # partition with the same account
            partition_ct = ContentType.objects.get_for_model(SlurmPartition)
            for other in qs.select_related("allocation"):
                other_alloc = other.allocation
                if (
                    other_alloc.resource_object_type_id == partition_ct.pk
                    and other_alloc.resource_object_id == resource.pk
                ):
                    raise ValidationError(
                        _(
                            "Another association already uses account "
                            "'%(account)s' for partition '%(partition)s' "
                            "on cluster '%(cluster)s'."
                        )
                        % {
                            "account": self.slurm_account.name,
                            "partition": resource.name,
                            "cluster": resource.cluster.name,
                        }
                    )

    clone_fields = (
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

    prerequisite_models = ("ras.Allocation",)

    def __str__(self):
        acct = self.slurm_account
        return f"Association {acct.name if acct else '?'} -> {self.allocation}"

    def get_status_color(self):
        return "green"


class SlurmUser(PrimaryModel):
    """
    Tracks each user's default account per cluster, matching Slurm's
    slurmdb_user_rec_t. This cleanly separates the default account concept
    from individual SlurmAssociation records.
    """

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="slurm_users",
        verbose_name=_("user"),
    )

    cluster = models.ForeignKey(
        to="slurm.SlurmCluster",
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name=_("cluster"),
    )

    default_account = models.ForeignKey(
        to="slurm.SlurmAccount",
        on_delete=models.PROTECT,
        related_name="default_for_users",
        verbose_name=_("default account"),
        help_text=_(
            "User's default Slurm account on this cluster. Jobs submitted "
            "by this user without specifying an account use this."
        ),
    )

    default_wckey = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("default wckey"),
        help_text=_("Default wckey for fairshare and accounting."),
    )

    default_qos = models.ForeignKey(
        to="slurm.SlurmQOS",
        on_delete=models.PROTECT,
        related_name="default_for_users",
        blank=True,
        null=True,
        verbose_name=_("default QOS"),
        help_text=_("Default QOS for this user on this cluster. Applies to all jobs regardless of association."),
    )

    admin_level = models.SmallIntegerField(
        choices=SlurmAdminLevelChoices,
        blank=True,
        null=True,
        verbose_name=_("admin level"),
        help_text=_(
            "Slurm administrator level for this user. Not Set (0), None (1), "
            "Operator (2), or Administrator (3). Operators can modify "
            "accounting entities; Administrators have full control."
        ),
    )

    clone_fields = (
        "cluster",
        "default_account",
        "default_wckey",
        "default_qos",
    )

    prerequisite_models = (
        "slurm.SlurmCluster",
        "slurm.SlurmAccount",
    )

    class Meta:
        ordering = ["cluster__name", "user__username"]
        verbose_name = _("slurm user")
        verbose_name_plural = _("slurm users")
        constraints = (
            models.UniqueConstraint(
                fields=("user", "cluster"),
                name="%(app_label)s_%(class)s_unique_user_cluster",
            ),
        )

    def __str__(self):
        return f"{self.user.username} ({self.cluster.name})"

    def get_status_color(self):
        return "green"
