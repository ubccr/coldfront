# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin utils.py"""

import datetime
import logging

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationUser,
    AllocationUserStatusChoice,
)
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.utils.common import import_from_settings

# Environment variables for auto_compute_allocation in utils.py
AUTO_COMPUTE_ALLOCATION_END_DELTA = import_from_settings("AUTO_COMPUTE_ALLOCATION_END_DELTA")
AUTO_COMPUTE_ALLOCATION_CHANGEABLE = import_from_settings("AUTO_COMPUTE_ALLOCATION_CHANGEABLE")
AUTO_COMPUTE_ALLOCATION_LOCKED = import_from_settings("AUTO_COMPUTE_ALLOCATION_LOCKED")
AUTO_COMPUTE_ALLOCATION_CLUSTERS = import_from_settings("AUTO_COMPUTE_ALLOCATION_CLUSTERS")
AUTO_COMPUTE_ALLOCATION_DESCRIPTION = import_from_settings("AUTO_COMPUTE_ALLOCATION_DESCRIPTION")

logger = logging.getLogger(__name__)


def get_cluster_resources_tuple():
    """Method to get all cluster Resources configured the Coldfront instance, optionally can filter out using variable"""
    # find 'Cluster' within ResourceType
    cluster_pk_value = ResourceType.objects.get(name="Cluster").pk
    # filter for clusters
    resource_queryset = Resource.objects.filter(resource_type=cluster_pk_value)
    # initialise a list which will store all clusters - even if just 1x
    cluster_list = []

    # If a filter is defined then find matches
    if AUTO_COMPUTE_ALLOCATION_CLUSTERS:
        for filter_cluster in AUTO_COMPUTE_ALLOCATION_CLUSTERS:
            matched_cluster = Resource.objects.get(name=filter_cluster)
            cluster_list.append(matched_cluster.pk)
        auto_allocation_clusters = tuple(cluster_list)
    # Otherwise all clusters
    else:
        for a_cluster in resource_queryset:
            cluster_list.append(a_cluster.pk)
        auto_allocation_clusters = tuple(cluster_list)
    return auto_allocation_clusters


# create the allocation
def allocation_auto_compute(project_obj, project_code):
    """Method to create the auto_compute allocation"""
    allocation_start_date = datetime.date.today()
    allocation_end_date = allocation_start_date + datetime.timedelta(days=AUTO_COMPUTE_ALLOCATION_END_DELTA)

    allocation_status_obj = AllocationStatusChoice.objects.get(name="New")  # alternative is Active
    allocation_description = f"{AUTO_COMPUTE_ALLOCATION_DESCRIPTION}{project_code}"

    allocation_obj = Allocation.objects.create(
        project=project_obj,
        justification="System automatically created compute allocation",
        description=allocation_description,
        status=allocation_status_obj,
        quantity=1,
        start_date=allocation_start_date,
        end_date=allocation_end_date,
        is_locked=AUTO_COMPUTE_ALLOCATION_LOCKED,  # admin needs to unlock to permit changes
        is_changeable=AUTO_COMPUTE_ALLOCATION_CHANGEABLE,
    )  # no ability to request change to this allocation
    return allocation_obj


def allocation_auto_compute_pi(project_obj, allocation_obj):
    """Method to add the PI to the auto_compute allocation - not other users, as they won't exist on project creation"""
    allocation_user_obj = AllocationUser.objects.create(
        allocation=allocation_obj,
        user=project_obj.pi,
        status=AllocationUserStatusChoice.objects.get(name="Active"),
    )
    return allocation_user_obj


def allocation_auto_compute_attribute_create(allocation_attribute_type_obj, allocation_obj, allocation_value):
    """generic method to add allocation attribute types and corresponding values"""
    allocation_attribute_obj = AllocationAttribute.objects.create(
        allocation=allocation_obj,
        allocation_attribute_type=allocation_attribute_type_obj,
        value=allocation_value,
    )
    return allocation_attribute_obj


def allocation_auto_compute_fairshare_institute(project_obj, allocation_obj):
    """method to add an institutional fair share value for slurm association - slurm specs"""
    if not hasattr(project_obj, "institution"):
        logger.info("Enable institution feature to set per institution fairshare in the auto_compute_allocation plugin")
        logger.info(
            "Additional message - this issue was encountered with project pk %s",
            {project_obj.pk},
        )
        return None
    if project_obj.institution in [None, "", "None"]:
        logger.info(
            "None or empty institution value encountered, an institution value is required to set per institution fairshare in the auto_compute_allocation plugin - value found was %s",
            {project_obj.institution},
        )
        logger.info(
            "Additional message - this issue was encountered with project pk",
            {project_obj.pk},
        )
        return None

    fairshare_institution = project_obj.institution

    allocation_attribute_type_obj = AllocationAttributeType.objects.get(name="slurm_specs")
    fairshare_value = f"Fairshare={fairshare_institution}"

    AllocationAttribute.objects.create(
        allocation=allocation_obj,
        allocation_attribute_type=allocation_attribute_type_obj,
        value=fairshare_value,
    )
