# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models

import coldfront.core.utils
import coldfront.models.deletion
import coldfront.utils.jsonschema


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0002_initial"),
        ("ras", "0003_projectinvite"),
        ("tenancy", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SlurmCluster",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "schema",
                    models.JSONField(
                        blank=True,
                        null=True,
                        validators=[coldfront.utils.jsonschema.validate_schema],
                        verbose_name="schema",
                    ),
                ),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text="Prevent users from submitting allocations for this resource.",
                        verbose_name="locked",
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "fairshare",
                    models.PositiveIntegerField(
                        blank=True,
                        default=1,
                        help_text="Default fairshare value for this cluster. Used as the root association's shares_raw. All associations under this cluster inherit unless overridden. Maps to Fairshare in the dump format.",
                        verbose_name="fairshare",
                    ),
                ),
                (
                    "features",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Cluster features (GPU types, etc.) used to describe federated cluster capabilities. When submitting a federated job, --features filters which cluster receives the job.",
                        null=True,
                        verbose_name="features",
                    ),
                ),
                (
                    "classification",
                    models.CharField(
                        blank=True,
                        help_text="How this machine is classified.",
                        max_length=50,
                        null=True,
                        verbose_name="classification",
                    ),
                ),
                (
                    "default_tres_billing_weights",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='TRES billing weights applied by default to partitions without their own. Maps to TRESBillingWeights on the PartitionName=DEFAULT line. An empty dict is treated as "{"CPU": 1.0}" (bill allocated CPUs).',
                        null=True,
                        verbose_name="default TRES billing weights",
                    ),
                ),
                (
                    "priority_flags",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Raw PriorityFlags from slurm.conf. Used to derive billing_mode (MAX_TRES / MAX_TRES_GRES).",
                        null=True,
                        verbose_name="priority flags",
                    ),
                ),
                (
                    "priority_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("priority/basic", "priority/basic"),
                            ("priority/multifactor", "priority/multifactor"),
                        ],
                        default="priority/multifactor",
                        help_text="Maps to PriorityType in slurm.conf. GrpTresMins enforcement requires priority/multifactor.",
                        max_length=50,
                        null=True,
                        verbose_name="priority type",
                    ),
                ),
                (
                    "priority_decay_half_life",
                    models.CharField(
                        blank=True,
                        default="7-0",
                        help_text="Raw string, e.g. 30-0 or 7-0. Maps to PriorityDecayHalfLife in slurm.conf.",
                        max_length=20,
                        null=True,
                        verbose_name="priority decay half life",
                    ),
                ),
                (
                    "priority_usage_reset_period",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("NONE", "NONE"),
                            ("NOW", "NOW"),
                            ("DAILY", "DAILY"),
                            ("WEEKLY", "WEEKLY"),
                            ("MONTHLY", "MONTHLY"),
                            ("QUARTERLY", "QUARTERLY"),
                            ("YEARLY", "YEARLY"),
                        ],
                        default="NONE",
                        help_text="Maps to PriorityUsageResetPeriod in slurm.conf.",
                        max_length=20,
                        null=True,
                        verbose_name="priority usage reset period",
                    ),
                ),
                (
                    "last_usage_sync",
                    models.DateField(
                        blank=True,
                        help_text="The last day successfully ingested by the SU usage sync job. The daily usage sync resumes from the day after this value, capped at USAGE_SYNC_MAX_CATCHUP_DAYS. On-demand syncs may advance it explicitly.",
                        null=True,
                        verbose_name="last usage sync",
                    ),
                ),
                (
                    "enforce_su_limits",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="ColdFront-only toggle. When enabled, service_units is pushed to Slurm as GrpTresMins=billing on the account association. Not a slurm.conf value. Enforcement requires PriorityType=priority/multifactor, is not enforced on the root account, and limits decayed usage (not a hard balance). For hard-cap behavior set PriorityDecayHalfLife=0 and a PriorityUsageResetPeriod.",
                        verbose_name="enforce SU limits",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="slurm_clusters",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm cluster",
                "verbose_name_plural": "slurm clusters",
                "ordering": ["name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SlurmAccount",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "fairshare",
                    models.PositiveIntegerField(
                        blank=True,
                        default=None,
                        help_text="Account-level fairshare. When set, all user associations under this account inherit via Fairshare=parent in the dump. ",
                        null=True,
                        verbose_name="fairshare",
                    ),
                ),
                (
                    "service_units",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Service units (SU) granted to this account. When the cluster's enforce_su_limits is on, this is pushed to Slurm as GrpTresMins=billing on the account association.",
                        null=True,
                        verbose_name="service units",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accounts",
                        to="slurm.slurmcluster",
                        verbose_name="cluster",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm account",
                "verbose_name_plural": "slurm accounts",
                "ordering": ["cluster__name", "name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SlurmQOS",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "priority",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="QOS priority factor. Higher values increase a job's priority when this QOS is used. Maps to Priority in the dump format.",
                        null=True,
                        verbose_name="priority",
                    ),
                ),
                (
                    "max_submit_jobs_per_user",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs a user can submit with this QOS. Maps to MaxSubmitJobsPU in the dump format.",
                        null=True,
                        verbose_name="max submit jobs per user",
                    ),
                ),
                (
                    "max_jobs_per_user",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of running jobs a user can have with this QOS. Maps to MaxJobsPU in the dump format.",
                        null=True,
                        verbose_name="max jobs per user",
                    ),
                ),
                (
                    "max_submit_jobs_per_account",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs an account can submit with this QOS. Maps to MaxSubmitJobsPA in the dump format.",
                        null=True,
                        verbose_name="max submit jobs per account",
                    ),
                ),
                (
                    "max_jobs_per_account",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of running jobs an account can have with this QOS. Maps to MaxJobsPA in the dump format.",
                        null=True,
                        verbose_name="max jobs per account",
                    ),
                ),
                (
                    "max_wall_duration_per_job",
                    models.DurationField(
                        blank=True,
                        help_text="Maximum wall clock time per job using this QOS. Maps to MaxWallDurationPerJob in the dump format.",
                        null=True,
                        verbose_name="max wall duration per job",
                    ),
                ),
                (
                    "limit_factor",
                    models.FloatField(
                        blank=True,
                        help_text="A float that is factored into an association's GrpTRES limits. Maps to LimitFactor in the dump format.",
                        null=True,
                        verbose_name="limit factor",
                    ),
                ),
                (
                    "grace_time",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Preemption grace time in seconds. Jobs selected for preemption are given this much time before termination. Maps to GraceTime in the dump format.",
                        null=True,
                        verbose_name="grace time",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm qos",
                "verbose_name_plural": "slurm qos",
                "ordering": ["name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.AddField(
            model_name="slurmcluster",
            name="default_qos",
            field=models.ForeignKey(
                blank=True,
                help_text="Default QOS applied to jobs that do not specify one. Maps to DefaultQOS in the dump format",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="default_for_clusters",
                to="slurm.slurmqos",
                verbose_name="default QOS",
            ),
        ),
        migrations.AddField(
            model_name="slurmcluster",
            name="qos_list",
            field=models.ManyToManyField(
                blank=True,
                help_text="QOS options available on this cluster. Associations inherit these via QOS+= syntax.",
                related_name="clusters",
                related_query_name="cluster",
                to="slurm.slurmqos",
                verbose_name="QOS list",
            ),
        ),
        migrations.CreateModel(
            name="SlurmAssociation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "fairshare",
                    models.PositiveIntegerField(
                        blank=True,
                        default=1,
                        help_text="Fairshare value for this association. Determines relative priority within the fairshare tree.",
                        verbose_name="fairshare",
                    ),
                ),
                (
                    "max_jobs",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs that can run simultaneously in this association.",
                        null=True,
                        verbose_name="max jobs",
                    ),
                ),
                (
                    "max_submit_jobs",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs that can be submitted by this association.",
                        null=True,
                        verbose_name="max submit jobs",
                    ),
                ),
                (
                    "max_tres_per_job",
                    models.JSONField(
                        blank=True,
                        help_text='JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).',
                        null=True,
                        verbose_name="max TRES per job",
                    ),
                ),
                (
                    "max_tres_mins_per_job",
                    models.JSONField(
                        blank=True,
                        help_text='JSON dict of TRES minute limits per job (e.g., {"cpu":360}).',
                        null=True,
                        verbose_name="max TRES minutes per job",
                    ),
                ),
                (
                    "max_wall_duration_per_job",
                    models.DurationField(
                        blank=True,
                        help_text="Maximum wall clock duration per job.",
                        null=True,
                        verbose_name="max wall duration per job",
                    ),
                ),
                (
                    "allocation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_extensions",
                        to="ras.allocation",
                        unique=True,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent account in the Slurm hierarchy for this association.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="child_associations",
                        to="slurm.slurmaccount",
                        verbose_name="parent account",
                    ),
                ),
                (
                    "slurm_account",
                    models.ForeignKey(
                        blank=True,
                        help_text="The Slurm account for this allocation. Links the allocation to a named Slurm accounting account.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="associations",
                        to="slurm.slurmaccount",
                        verbose_name="Slurm account",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "default_qos",
                    models.ForeignKey(
                        blank=True,
                        help_text="Default QOS for this association. Jobs under this association inherit this QOS unless they specify one.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="associations",
                        to="slurm.slurmqos",
                        verbose_name="default QOS",
                    ),
                ),
                (
                    "qos_add",
                    models.ManyToManyField(
                        blank=True,
                        help_text="QOSes to add to this association via QOS+= in the dump format. These are added on top of the cluster/account defaults.",
                        related_name="added_to_associations",
                        related_query_name="added_to_association",
                        to="slurm.slurmqos",
                        verbose_name="QOS add",
                    ),
                ),
                (
                    "qos_remove",
                    models.ManyToManyField(
                        blank=True,
                        help_text="QOSes to remove from this association via QOS-= in the dump format. These are subtracted from the inherited QOS list.",
                        related_name="removed_from_associations",
                        related_query_name="removed_from_association",
                        to="slurm.slurmqos",
                        verbose_name="QOS remove",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm association",
                "verbose_name_plural": "slurm associations",
                "ordering": ["allocation__slug"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.AddField(
            model_name="slurmaccount",
            name="qos_add",
            field=models.ManyToManyField(
                blank=True,
                help_text="QOSes to add to this account via QOS+= in the dump format. These are added on top of the cluster defaults.",
                related_name="added_to_accounts",
                related_query_name="added_to_account",
                to="slurm.slurmqos",
                verbose_name="QOS add",
            ),
        ),
        migrations.AddField(
            model_name="slurmaccount",
            name="qos_remove",
            field=models.ManyToManyField(
                blank=True,
                help_text="QOSes to remove from this account via QOS-= in the dump format. These are subtracted from the inherited QOS list.",
                related_name="removed_from_accounts",
                related_query_name="removed_from_account",
                to="slurm.slurmqos",
                verbose_name="QOS remove",
            ),
        ),
        migrations.CreateModel(
            name="SlurmUser",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "default_wckey",
                    models.CharField(
                        blank=True,
                        help_text="Default wckey for fairshare and accounting.",
                        max_length=100,
                        null=True,
                        verbose_name="default wckey",
                    ),
                ),
                (
                    "admin_level",
                    models.SmallIntegerField(
                        blank=True,
                        choices=[(0, "Not Set"), (1, "None"), (2, "Operator"), (3, "Administrator")],
                        help_text="Slurm administrator level for this user. Not Set (0), None (1), Operator (2), or Administrator (3). Operators can modify accounting entities; Administrators have full control.",
                        null=True,
                        verbose_name="admin level",
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="users",
                        to="slurm.slurmcluster",
                        verbose_name="cluster",
                    ),
                ),
                (
                    "default_account",
                    models.ForeignKey(
                        help_text="User's default Slurm account on this cluster. Jobs submitted by this user without specifying an account use this.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="default_for_users",
                        to="slurm.slurmaccount",
                        verbose_name="default account",
                    ),
                ),
                (
                    "default_qos",
                    models.ForeignKey(
                        blank=True,
                        help_text="Default QOS for this user on this cluster. Applies to all jobs regardless of association.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="default_for_users",
                        to="slurm.slurmqos",
                        verbose_name="default QOS",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="slurm_users",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm user",
                "verbose_name_plural": "slurm users",
                "ordering": ["cluster__name", "user__username"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SlurmAccountUsage",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "period_start",
                    models.DateField(
                        help_text="First day of the usage period (inclusive).", verbose_name="period start"
                    ),
                ),
                (
                    "period_end",
                    models.DateField(help_text="Last day of the usage period (inclusive).", verbose_name="period end"),
                ),
                (
                    "billing_units_consumed",
                    models.FloatField(
                        default=0.0,
                        help_text="Billable SU attributed to this day (overlap-based). Billed number.",
                        verbose_name="billing units consumed",
                    ),
                ),
                (
                    "walltime_sec_consumed",
                    models.BigIntegerField(
                        default=0,
                        help_text="Total job walltime seconds (one node) attributed to this day.",
                        verbose_name="walltime seconds consumed",
                    ),
                ),
                (
                    "node_hours_consumed",
                    models.FloatField(
                        default=0.0,
                        help_text="Node-hours attributed to this day (node count x overlap hours).",
                        verbose_name="node hours consumed",
                    ),
                ),
                (
                    "job_count_consumed",
                    models.PositiveIntegerField(
                        default=0, help_text="Number of jobs overlapping this day.", verbose_name="job count consumed"
                    ),
                ),
                (
                    "billing_units_completed",
                    models.FloatField(
                        default=0.0,
                        help_text="Billable SU charged on the day jobs completed (full elapsed). Informational.",
                        verbose_name="billing units completed",
                    ),
                ),
                (
                    "walltime_sec_completed",
                    models.BigIntegerField(
                        default=0,
                        help_text="Total job walltime seconds (one node) of jobs completing this day.",
                        verbose_name="walltime seconds completed",
                    ),
                ),
                (
                    "job_count_completed",
                    models.PositiveIntegerField(
                        default=0, help_text="Number of jobs completing this day.", verbose_name="job count completed"
                    ),
                ),
                (
                    "node_hours_by_partition",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Dict of partition name -> node-hours consumed that day.",
                        verbose_name="node hours by partition",
                    ),
                ),
                (
                    "billing_by_qos",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Dict of QOS name -> billing units consumed that day.",
                        verbose_name="billing by QOS",
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usages",
                        to="slurm.slurmaccount",
                        verbose_name="account",
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="account_usages",
                        to="slurm.slurmcluster",
                        verbose_name="cluster",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm account usage",
                "verbose_name_plural": "slurm account usage",
                "ordering": ["cluster__name", "account__name", "period_start"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("cluster", "account", "period_start"),
                        name="slurm_slurmaccountusage_unique_cluster_account_day",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SlurmPartition",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "schema",
                    models.JSONField(
                        blank=True,
                        null=True,
                        validators=[coldfront.utils.jsonschema.validate_schema],
                        verbose_name="schema",
                    ),
                ),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text="Prevent users from submitting allocations for this resource.",
                        verbose_name="locked",
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "max_jobs",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs that can run simultaneously in this partition.",
                        null=True,
                        verbose_name="max jobs",
                    ),
                ),
                (
                    "max_submit_jobs",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of jobs that can be submitted by this association.",
                        null=True,
                        verbose_name="max submit jobs",
                    ),
                ),
                (
                    "max_tres_per_job",
                    models.JSONField(
                        blank=True,
                        help_text='JSON dict of TRES limits per job (e.g., {"node":5,"cpu":20}).',
                        null=True,
                        verbose_name="max TRES per job",
                    ),
                ),
                (
                    "max_tres_per_node",
                    models.JSONField(
                        blank=True,
                        help_text='JSON dict of TRES limits per node (e.g., {"gpu":8}).',
                        null=True,
                        verbose_name="max TRES per node",
                    ),
                ),
                (
                    "max_tres_mins_per_job",
                    models.JSONField(
                        blank=True,
                        help_text='JSON dict of TRES minute limits per job (e.g., {"cpu":360}).',
                        null=True,
                        verbose_name="max TRES minutes per job",
                    ),
                ),
                (
                    "max_wall_duration_per_job",
                    models.DurationField(
                        blank=True,
                        help_text="Maximum wall clock duration per job.",
                        null=True,
                        verbose_name="max wall duration per job",
                    ),
                ),
                (
                    "fairshare",
                    models.PositiveIntegerField(
                        blank=True,
                        default=1,
                        help_text="Fairshare value for this partition's associations. Determines relative priority within the fairshare tree. Higher values allow more jobs before priority decays.",
                        verbose_name="fairshare",
                    ),
                ),
                (
                    "nodes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Comma-separated node list for this partition (e.g., node[01-64]).",
                        verbose_name="nodes",
                    ),
                ),
                (
                    "priority",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Priority tier for scheduling and preemption. Higher priority partitions are scheduled first.",
                        null=True,
                        verbose_name="priority",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="If set, this is the default partition for jobs that do not specify one.",
                        verbose_name="default",
                    ),
                ),
                (
                    "default_time",
                    models.DurationField(
                        blank=True,
                        help_text="Default job time limit for this partition.",
                        null=True,
                        verbose_name="default time",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        blank=True,
                        choices=[("UP", "UP"), ("DOWN", "DOWN"), ("DRAIN", "DRAIN"), ("INACTIVE", "INACTIVE")],
                        help_text="Partition state (UP, DOWN, DRAIN, INACTIVE).",
                        max_length=20,
                        null=True,
                        verbose_name="state",
                    ),
                ),
                (
                    "preempt_mode",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("OFF", "OFF"),
                            ("SUSPEND", "SUSPEND"),
                            ("REQUEUE", "REQUEUE"),
                            ("CANCEL", "CANCEL"),
                            ("GANG", "GANG"),
                            ("WITHIN", "WITHIN"),
                            ("PRIORITY", "PRIORITY"),
                        ],
                        help_text="Preemption mode for this partition (e.g., OFF, SUSPEND, GANG, CANCEL).",
                        max_length=20,
                        null=True,
                        verbose_name="preempt mode",
                    ),
                ),
                (
                    "def_mem_per_cpu",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Default memory per CPU in MB for jobs in this partition.",
                        null=True,
                        verbose_name="default memory per CPU",
                    ),
                ),
                (
                    "tres_billing_weights",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="TRES billing weights for this partition. Maps to TRESBillingWeights on the PartitionName=<name> line. An empty dict falls through to the cluster's default_tres_billing_weights.",
                        null=True,
                        verbose_name="TRES billing weights",
                    ),
                ),
                ("slug", models.SlugField(blank=True, max_length=100, unique=True, verbose_name="slug")),
                (
                    "allow_accounts",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Restrict which SlurmAccounts can submit jobs to this partition. When set, only associations under one of these accounts are permitted.",
                        related_name="allowed_partitions",
                        related_query_name="allowed_partition",
                        to="slurm.slurmaccount",
                        verbose_name="allowed accounts",
                    ),
                ),
                (
                    "allow_groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Restrict partition access to specific ColdFront Groups. Users must be in one of these groups to submit allocations to this partition. Maps to AllowGroups in slurm.conf.",
                        related_name="allowed_partitions",
                        related_query_name="allowed_partition",
                        to="users.group",
                        verbose_name="allowed groups",
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="partitions",
                        to="slurm.slurmcluster",
                        verbose_name="cluster",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "allow_qos",
                    models.ManyToManyField(
                        blank=True,
                        help_text="QOS whitelist for admission control. Only jobs requesting one of these QOSes are permitted to submit to this partition. Maps to AllowQOS in slurm.conf.",
                        related_name="allowed_partitions",
                        related_query_name="allowed_partition",
                        to="slurm.slurmqos",
                        verbose_name="allowed QOS",
                    ),
                ),
                (
                    "qos",
                    models.ForeignKey(
                        blank=True,
                        help_text="Partition-level QOS whose resource limits (max time, CPUs, memory) apply to every job in this partition. The partition QOS and the job's QOS are both enforced — the stricter limit wins. Maps to QOS in slurm.conf.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assigned_partitions",
                        to="slurm.slurmqos",
                        verbose_name="QOS",
                    ),
                ),
            ],
            options={
                "verbose_name": "slurm partition",
                "verbose_name_plural": "slurm partitions",
                "ordering": ["cluster__name", "name"],
                "constraints": [
                    models.UniqueConstraint(fields=("cluster", "name"), name="slurm_slurmpartition_unique_cluster_name")
                ],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name="slurmaccount",
            constraint=models.UniqueConstraint(
                fields=("cluster", "name"), name="slurm_slurmaccount_unique_cluster_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="slurmuser",
            constraint=models.UniqueConstraint(fields=("user", "cluster"), name="slurm_slurmuser_unique_user_cluster"),
        ),
    ]
