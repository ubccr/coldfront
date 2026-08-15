# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.constants import BOOLEAN_WITH_BLANK_CHOICES
from coldfront.forms import PrimaryModelFilterSetForm
from coldfront.forms.fields import TagFilterField
from coldfront.ras.models import Allocation
from coldfront.slurm.choices import (
    SlurmAdminLevelChoices,
    SlurmPartitionStateChoices,
    SlurmPreemptModeChoices,
)
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmPartition, SlurmQOS, SlurmUser
from coldfront.users.models import User
from coldfront.utils.forms import add_blank_choice


class SlurmQOSFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmQOS
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm QOS"),
            "tag",
        ),
    )


class SlurmClusterFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmCluster
    locked = forms.NullBooleanField(
        label=_("Locked"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    default_qos_id = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
    )
    classification = forms.CharField(
        required=False,
        label=_("Classification"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm Cluster"),
            "locked",
            "default_qos_id",
            "classification",
            "tag",
        ),
    )


class SlurmPartitionFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmPartition
    cluster_id = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    state = forms.MultipleChoiceField(
        label=_("State"),
        choices=SlurmPartitionStateChoices,
        required=False,
    )
    is_default = forms.NullBooleanField(
        label=_("Default"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    preempt_mode = forms.MultipleChoiceField(
        label=_("Preempt Mode"),
        choices=SlurmPreemptModeChoices,
        required=False,
    )
    qos_id = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("QOS"),
    )
    locked = forms.NullBooleanField(
        label=_("Locked"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm Partition"),
            "cluster_id",
            "state",
            "is_default",
            "preempt_mode",
            "qos_id",
            "locked",
            "tag",
        ),
    )


class SlurmAccountFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmAccount
    cluster_id = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm Account"),
            "cluster_id",
            "tag",
        ),
    )


class SlurmAssociationFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmAssociation
    slurm_account_id = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Slurm Account"),
    )
    allocation_id = forms.ModelChoiceField(
        queryset=Allocation.objects.all(),
        required=False,
        label=_("Allocation"),
    )
    parent_id = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Parent Account"),
    )
    default_qos_id = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm Association"),
            "slurm_account_id",
            "allocation_id",
            "parent_id",
            "default_qos_id",
            "tag",
        ),
    )


class SlurmUserFilterSetForm(PrimaryModelFilterSetForm):
    model = SlurmUser
    cluster_id = forms.ModelChoiceField(
        queryset=SlurmCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("User"),
    )
    default_account_id = forms.ModelChoiceField(
        queryset=SlurmAccount.objects.all(),
        required=False,
        label=_("Default Account"),
    )
    default_qos_id = forms.ModelChoiceField(
        queryset=SlurmQOS.objects.all(),
        required=False,
        label=_("Default QOS"),
    )
    admin_level = forms.ChoiceField(
        label=_("Admin Level"),
        choices=add_blank_choice(SlurmAdminLevelChoices),
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Slurm User"),
            "cluster_id",
            "user_id",
            "default_account_id",
            "default_qos_id",
            "admin_level",
            "tag",
        ),
    )
