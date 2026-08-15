# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.db import models
from django.db.models import Q
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _

from coldfront.models import PrimaryModel
from coldfront.models.features import AllocatableResourceMixin
from coldfront.ras.models.mixins import AllocationExtensionMixin
from coldfront.registry import register_allocation_extension

from .choices import StorageShareTypeChoices, StorageSnapshotIntervalChoices


class StorageResource(AllocatableResourceMixin, PrimaryModel):
    """
    An allocatable resource that represents a storage system (VAST, PureStorage,
    GPFS, etc.).  Users request an allocation to a ``StorageResource`` and then
    specify the requested quota amount on a separate post-request form.

    Each ``StorageResource`` is backed by one or more ``StorageCluster``
    instances (M2M).  The cluster provides the backend that creates paths
    and quotas.
    """

    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="storage_resources",
        blank=True,
        null=True,
        verbose_name=_("tenant"),
    )

    clusters = models.ManyToManyField(
        to="storage.StorageCluster",
        related_name="storage_resources",
        verbose_name=_("clusters"),
    )

    path_template = models.CharField(
        verbose_name=_("path template"),
        max_length=500,
        default="/mnt/{{project.slug}}/{{allocation.slug}}",
        help_text=_(
            "Template for auto-generating storage paths. Supports "
            "{project.<attr>}, {resource.<attr>}, and {allocation.id}."
        ),
    )

    capacity_bytes = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        default=None,
        verbose_name=_("capacity"),
        help_text=_("Maximum total allocation across all quotas on this resource. Leave empty for unlimited."),
    )

    allocated_bytes = models.PositiveBigIntegerField(
        default=0,
        editable=False,
        verbose_name=_("allocated"),
        help_text=_("Sum of hard_limit_bytes for all active quotas. Updated automatically."),
    )

    used_bytes = models.PositiveBigIntegerField(
        default=0,
        editable=False,
        verbose_name=_("used"),
        help_text=_("Sum of actual usage from all active quotas. Updated by sync."),
    )

    clone_fields = (
        "locked",
        "tenant",
        "clusters",
        "path_template",
        "capacity_bytes",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("storage resource")
        verbose_name_plural = _("storage resources")
        constraints = (
            models.CheckConstraint(
                condition=Q(capacity_bytes=None) | Q(capacity_bytes__gt=0),
                name="%(app_label)s_%(class)s_capacity_must_be_null_or_positive",
            ),
        )

    def __str__(self):
        return self.name

    def get_status_color(self):
        return "green"

    def auto_generate_path(self, allocation):
        """Generate a storage path from the resource's path_template.

        Uses Django's template engine for rendering. The template may
        reference ``{{ allocation }}``, ``{{ project.slug }}``,
        ``{{ allocation.id }}``, ``{{ resource.<field> }}``, etc.
        """

        tpl = self.path_template
        if not tpl:
            return f"/mnt/{allocation.project.slug}/{allocation.slug}"

        context = Context(
            {
                "project": allocation.project,
                "allocation": allocation,
                "resource": self,
            }
        )
        template = Template(tpl)
        return template.render(context)


class StorageCluster(PrimaryModel):
    """
    Represents a storage cluster that provides the backend for creating paths
    and quotas.  A ``StorageResource`` may use multiple clusters (e.g., a VAST
    system with multiple VMS endpoints), and a cluster may serve multiple
    ``StorageResource`` instances (e.g., Project storage and Scratch storage
    on the same VAST array).

    The cluster carries no connection settings — only the ``backend_path``,
    which is a dotted Python path to a ``StorageBackend`` subclass.  Each
    backend handles its own configuration.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        verbose_name=_("description"),
        blank=True,
    )

    backend_path = models.CharField(
        verbose_name=_("backend path"),
        max_length=500,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            "Dotted Python path to a StorageBackend subclass, e.g. 'coldfront.storage.backends.vast.VastBackend'. "
            "Leave empty for clusters with no backend (sync jobs will skip them)."
        ),
    )

    auto_sync_enabled = models.BooleanField(
        verbose_name=_("auto sync enabled"),
        default=False,
    )

    sync_interval = models.IntegerField(
        verbose_name=_("sync interval"),
        default=1440,
        help_text=_("Minutes between automatic syncs."),
    )

    capacity_bytes = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        default=None,
        verbose_name=_("capacity"),
        help_text=_("Total storage capacity of this cluster in bytes. Leave empty for unlimited."),
    )

    allocated_bytes = models.PositiveBigIntegerField(
        default=0,
        editable=False,
        verbose_name=_("allocated"),
        help_text=_("Sum of hard_limit_bytes for all active quotas on this cluster. Updated automatically."),
    )

    used_bytes = models.PositiveBigIntegerField(
        default=0,
        editable=False,
        verbose_name=_("used"),
        help_text=_("Sum of actual usage from all active quotas on this cluster. Updated by sync."),
    )

    clone_fields = (
        "description",
        "backend_path",
        "auto_sync_enabled",
        "sync_interval",
        "capacity_bytes",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("storage cluster")
        verbose_name_plural = _("storage clusters")
        constraints = (
            models.CheckConstraint(
                condition=Q(capacity_bytes=None) | Q(capacity_bytes__gt=0),
                name="%(app_label)s_%(class)s_capacity_must_be_null_or_positive",
            ),
        )

    def __str__(self):
        return self.name

    def get_status_color(self):
        return "green"


@register_allocation_extension(StorageResource)
class StorageQuota(AllocationExtensionMixin, PrimaryModel):
    """
    Carries resource-specific quota data for an allocation on a
    ``StorageResource``.  Created when the allocation is created, and
    updated via change requests.

    The ``clusters`` M2M is nullable:
    - If empty — the quota applies to ALL clusters associated with ``quota.storage.clusters``
    - If set — the quota applies only to the selected clusters
    """

    _requestable_fields = ["hard_limit_bytes", "hard_limit_files"]

    @classmethod
    def requestable_fields_overrides(cls):
        """
        Use ``BytesField`` for byte-size fields so users can input
        human-readable sizes like ``"10 TB"`` instead of raw integers.
        """
        from coldfront.forms.fields.bytes import BytesField

        return {
            "hard_limit_bytes": BytesField(
                label=_("Hard Limit"),
                help_text=_("Quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
            ),
            "hard_limit_files": forms.IntegerField(
                label=_("Hard Limit Files"),
                help_text=_("Hard limit on the number of files."),
            ),
        }

    class Meta:
        ordering = ["allocation__slug"]
        verbose_name = _("storage quota")
        verbose_name_plural = _("storage quotas")
        constraints = (
            models.UniqueConstraint(
                fields=("path", "storage"),
                name="%(app_label)s_%(class)s_unique_path_per_storage",
            ),
        )

    storage = models.ForeignKey(
        to="storage.StorageResource",
        on_delete=models.PROTECT,
        related_name="quotas",
        verbose_name=_("storage resource"),
    )

    clusters = models.ManyToManyField(
        to="storage.StorageCluster",
        blank=True,
        related_name="quotas",
        verbose_name=_("clusters"),
    )

    path = models.CharField(
        verbose_name=_("path"),
        max_length=500,
    )

    owning_user = models.ForeignKey(
        to="users.User",
        on_delete=models.PROTECT,
        related_name="storage_quotas_as_owner",
        verbose_name=_("owning user"),
        blank=True,
        null=True,
    )

    owning_group = models.ForeignKey(
        to="users.Group",
        on_delete=models.PROTECT,
        related_name="storage_quotas",
        verbose_name=_("owning group"),
        blank=True,
        null=True,
    )

    path_mode = models.PositiveSmallIntegerField(
        verbose_name=_("path mode"),
        default=2770,
    )

    hard_limit_bytes = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("hard limit"),
        help_text=_("Quota limit in bytes."),
    )

    soft_limit_bytes = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("soft limit"),
        help_text=_("Soft quota limit in bytes."),
    )

    hard_limit_files = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("hard limit files"),
        help_text=_("Hard limit on number of files."),
    )

    soft_limit_files = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("soft limit files"),
        help_text=_("Soft limit on number of files."),
    )

    grace_period = models.DurationField(
        blank=True,
        null=True,
        verbose_name=_("grace period"),
    )

    share_type = models.CharField(
        verbose_name=_("share type"),
        max_length=20,
        choices=StorageShareTypeChoices,
        default=StorageShareTypeChoices.SHARE_TYPE_POSIX,
    )

    used = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("used"),
        help_text=_("Current usage in bytes. Populated by sync."),
    )

    used_files = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name=_("used files"),
        help_text=_("Current number of files. Populated by sync."),
    )

    state = models.CharField(
        verbose_name=_("state"),
        max_length=50,
        blank=True,
    )

    snapshot_policy = models.ForeignKey(
        to="storage.StorageSnapshotPolicy",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quotas",
        verbose_name=_("snapshot policy"),
    )

    clone_fields = (
        "storage",
        "clusters",
        "path",
        "owning_user",
        "owning_group",
        "path_mode",
        "hard_limit_bytes",
        "soft_limit_bytes",
        "hard_limit_files",
        "soft_limit_files",
        "grace_period",
        "share_type",
        "snapshot_policy",
    )

    prerequisite_models = (
        "ras.Allocation",
        "storage.StorageResource",
    )

    def __str__(self):
        return f"Quota {self.path} -> {self.allocation}"

    def get_status_color(self):
        return "green"

    @classmethod
    def create_for_allocation(cls, allocation, values=None):
        """
        Create a StorageQuota instance for the given allocation.
        """
        resource = allocation.resource_object
        if not isinstance(resource, StorageResource):
            # XXX This should never happen but what todo?
            return

        kwargs = {}
        kwargs["storage"] = resource
        kwargs["path"] = resource.auto_generate_path(allocation)
        kwargs["owning_user"] = allocation.project.owner

        if allocation.project.group:
            kwargs["owning_group"] = allocation.project.group

        if values is not None:
            for field_name in cls.requestable_fields():
                if field_name in values:
                    kwargs[field_name] = values[field_name]

        instance = StorageQuota(allocation=allocation, **kwargs)
        instance.full_clean()
        instance.save()
        return instance


class StorageSnapshotPolicy(PrimaryModel):
    """
    A reusable snapshot policy definition attached to a cluster.  Each cluster
    can define multiple policies (e.g., "daily-7d", "hourly-30d"), and each
    quota can select one.

    NOTE: When ``StorageQuota`` has M2M clusters, the ``snapshot_policy`` FK
    is applied only to its owning cluster (``quota.snapshot_policy.cluster``).
    Other clusters in the quota's cluster set do NOT receive snapshot
    protection unless they have their own policy selected.
    """

    cluster = models.ForeignKey(
        to="storage.StorageCluster",
        on_delete=models.PROTECT,
        related_name="snapshot_policies",
        verbose_name=_("cluster"),
    )

    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
    )

    interval = models.CharField(
        verbose_name=_("interval"),
        max_length=50,
        choices=StorageSnapshotIntervalChoices,
    )

    retention_days = models.PositiveIntegerField(
        verbose_name=_("retention days"),
        help_text=_("Number of days to retain snapshots."),
    )

    extra_config = models.JSONField(
        blank=True,
        default=dict,
        verbose_name=_("extra configuration"),
    )

    clone_fields = (
        "cluster",
        "name",
        "interval",
        "retention_days",
        "extra_config",
    )

    prerequisite_models = ("storage.StorageCluster",)

    class Meta:
        ordering = ["cluster__name", "name"]
        verbose_name = _("storage snapshot policy")
        verbose_name_plural = _("storage snapshot policies")
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
