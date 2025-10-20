# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront auto_compute_allocation plugin tasks.py"""

import logging

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.auto_compute_allocation.slurm_account_name import generate_slurm_account_name
from coldfront.plugins.auto_compute_allocation.utils import (
    allocation_auto_compute,
    allocation_auto_compute_attribute_create,
    allocation_auto_compute_fairshare_institution,
    allocation_auto_compute_pi,
    get_cluster_resources_tuple,
)

logger = logging.getLogger(__name__)

# Environment variables for auto_compute_allocation in tasks.py
AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS = import_from_settings("AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS")
AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING = import_from_settings(
    "AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING"
)
AUTO_COMPUTE_ALLOCATION_CORE_HOURS = import_from_settings("AUTO_COMPUTE_ALLOCATION_CORE_HOURS")
AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING = import_from_settings("AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING")
AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION = import_from_settings("AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION")
AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE = import_from_settings("AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE")
AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING = import_from_settings(
    "AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING"
)


# automatically create a compute allocation, called by project_new signal
def add_auto_compute_allocation(project_obj):
    """Method to add a compute allocation automatically upon project creation - uses signals for project creation"""

    # if project_code not enabled or None or empty, print appropriate message and stop
    if not hasattr(project_obj, "project_code"):
        logger.info("Enable project_code to use the auto_compute_allocation plugin")
        logger.info(
            "Additional message - this issue was encountered with project pk %s",
            {project_obj.pk},
        )
        return None
    if project_obj.project_code in [None, ""]:
        logger.info("None or empty project_code value encountered, please run the project code management command")
        logger.info(
            "Additional message - this issue was encountered with project pk %s",
            {project_obj.pk},
        )
        return None

    project_code = project_obj.project_code
    auto_allocation_clusters = get_cluster_resources_tuple()

    if len(auto_allocation_clusters) == 0:
        raise Exception("No auto_allocation_clusters found - no resources of type Cluster configured!")

    # accelerator hours
    allocation_attribute_type_obj_accelerator_hours = AllocationAttributeType.objects.get(
        name="Accelerator Usage (Hours)"
    )
    # core hours
    allocation_attribute_type_obj_core_hours = AllocationAttributeType.objects.get(name="Core Usage (Hours)")
    # slurm account name
    allocation_attribute_type_obj_slurm_account_name = AllocationAttributeType.objects.get(name="slurm_account_name")
    # slurm specs
    allocation_attribute_type_obj_slurm_specs = AllocationAttributeType.objects.get(name="slurm_specs")
    # slurm user specs
    allocation_attribute_type_obj_slurm_user_specs = AllocationAttributeType.objects.get(name="slurm_user_specs")

    try:
        # create the allocation and return it
        allocation_obj = allocation_auto_compute(project_obj, project_code)
    except Exception as e:
        logger.error("Failed to add auto_compute_allocation: %s", e)

    try:
        # add all clusters in the tuple, which might just be 1x
        allocation_obj.resources.add(*auto_allocation_clusters)

    except Exception as e:
        logger.error("Failed to add Cluster resource(s) to auto_compute_allocation: %s", e)

    try:
        # allocation user - PI
        allocation_auto_compute_pi(project_obj, allocation_obj)
    except Exception as e:
        logger.error("Failed to add PI to auto_compute_allocation: %s", e)

    # get the format of the slurm account name
    local_slurm_account_name = generate_slurm_account_name(allocation_obj, project_obj)

    try:
        # add the slurm account name
        allocation_auto_compute_attribute_create(
            allocation_attribute_type_obj_slurm_account_name,
            allocation_obj,
            local_slurm_account_name,
        )
    except Exception as e:
        logger.error("Failed to add slurm account name to auto_compute_allocation: %s", e)

    try:
        # add slurm user specs
        fairshare_value = "Fairshare=parent"
        # use generic function
        allocation_auto_compute_attribute_create(
            allocation_attribute_type_obj_slurm_user_specs,
            allocation_obj,
            fairshare_value,
        )
    except Exception as e:
        logger.error("Failed to add fairshare value to auto_compute_allocation: %s", e)

    if project_obj.field_of_science.description != "Training":
        # 1a) add accelerator hours non-training project - for gauge to appear
        if AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS > 0:
            accelerator_hours_quantity = AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS
            allocation_auto_compute_attribute_create(
                allocation_attribute_type_obj_accelerator_hours,
                allocation_obj,
                accelerator_hours_quantity,
            )
        # 1b) add core hours non-training project - for gauge to appear
        if AUTO_COMPUTE_ALLOCATION_CORE_HOURS > 0:
            core_hours_quantity = AUTO_COMPUTE_ALLOCATION_CORE_HOURS
            allocation_auto_compute_attribute_create(
                allocation_attribute_type_obj_core_hours,
                allocation_obj,
                core_hours_quantity,
            )
        # 1c) add slurm attrs non-training project
        if len(AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE) > 0:
            for slurm_attr in AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE:
                new_slurm_attr = slurm_attr.replace(";", ",").replace("'", "")
                allocation_auto_compute_attribute_create(
                    allocation_attribute_type_obj_slurm_specs,
                    allocation_obj,
                    new_slurm_attr,
                )

    if project_obj.field_of_science.description == "Training":
        # 2a) add accelerator hours training project - for gauge to appear
        if AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING > 0:
            accelerator_hours_quantity = AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING
            allocation_auto_compute_attribute_create(
                allocation_attribute_type_obj_accelerator_hours,
                allocation_obj,
                accelerator_hours_quantity,
            )
        # 2b) add core hours training project - for gauge to appear
        if AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING > 0:
            core_hours_quantity = AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING
            allocation_auto_compute_attribute_create(
                allocation_attribute_type_obj_core_hours,
                allocation_obj,
                core_hours_quantity,
            )
        # 2c) add slurm attrs training project
        if len(AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING) > 0:
            for slurm_attr in AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING:
                new_slurm_attr = slurm_attr.replace(";", ",").replace("'", "")
                allocation_auto_compute_attribute_create(
                    allocation_attribute_type_obj_slurm_specs,
                    allocation_obj,
                    new_slurm_attr,
                )

    if AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION:
        allocation_auto_compute_fairshare_institution(project_obj, allocation_obj)
