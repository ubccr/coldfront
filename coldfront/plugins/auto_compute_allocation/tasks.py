import logging

from coldfront.core.utils.common import import_from_settings

from coldfront.core.allocation.models import (Allocation,
                                             AllocationAttribute,
                                             AllocationAttributeType,
                                             AllocationStatusChoice,
                                             AllocationUser,
                                             AllocationUserStatusChoice)

from coldfront.core.project.models import Project

from coldfront.plugins.auto_compute_allocation.utils import (get_cluster_resources_tuple,
                                                            allocation_auto_compute,
                                                            allocation_auto_compute_attribute_create,
                                                            allocation_auto_compute_fairshare_institute,
                                                            allocation_auto_compute_pi)

logger = logging.getLogger(__name__)

# Environment variables for auto_compute_allocation in tasks.py
AUTO_COMPUTE_ALLOCATION_CORE_HOURS = import_from_settings('AUTO_COMPUTE_ALLOCATION_CORE_HOURS')
AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING = import_from_settings('AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING')
AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION = import_from_settings('AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION')

# automatically create a compute allocation, called by project_new signal
def add_auto_compute_allocation(project_obj):
    """ Method to add a compute allocation automatically upon project creation - uses signals for project creation """

    project_code = project_obj.project_code
    auto_allocation_clusters = get_cluster_resources_tuple()

    # core hours
    allocation_attribute_type_obj_core_hours = AllocationAttributeType.objects.get(name='Core Usage (Hours)')
    # slurm account name
    allocation_attribute_type_obj_slurm_account_name = AllocationAttributeType.objects.get(name='slurm_account_name')
    # slurm user specs
    allocation_attribute_type_obj_slurm_user_specs = AllocationAttributeType.objects.get(name='slurm_user_specs')


    try:
        # create the allocation and return it
        allocation_obj = allocation_auto_compute(project_obj, project_code)

        # add all clusters in the tuple, which might just be 1x
        allocation_obj.resources.add(* auto_allocation_clusters)

        # allocation user - PI
        allocation_auto_compute_pi(project_obj, allocation_obj)

        # add the slurm account name
        allocation_auto_compute_attribute_create(allocation_attribute_type_obj_slurm_account_name, allocation_obj, project_code)

        # add slurm user specs
        fairshare_value="Fairshare=parent"
        allocation_auto_compute_attribute_create(allocation_attribute_type_obj_slurm_user_specs, allocation_obj, fairshare_value)

    except:
        logger.error("Failed to add auto_compute_allocation")
        
    # add core hours non-training project
    if AUTO_COMPUTE_ALLOCATION_CORE_HOURS > 0 and project_obj.field_of_science.description != 'Training':
        core_hours_quantity = AUTO_COMPUTE_ALLOCATION_CORE_HOURS
        allocation_auto_compute_attribute_create(allocation_attribute_type_obj_core_hours, allocation_obj, core_hours_quantity)
    # add core hours training project
    elif AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING > 0 and project_obj.field_of_science.description == 'Training':
        core_hours_quantity = AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING
        allocation_auto_compute_attribute_create(allocation_attribute_type_obj_core_hours, allocation_obj, core_hours_quantity)

    # finally if enabled, add the institution based fairshare
    if AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION:
        allocation_auto_compute_fairshare_institute(project_obj, allocation_obj, project_code)
