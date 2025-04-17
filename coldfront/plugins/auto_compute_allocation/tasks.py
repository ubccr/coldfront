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
                                                            allocation_auto_compute_pi,
                                                            allocation_auto_compute_slurm,
                                                            allocation_auto_compute_fairshare,
                                                            allocation_auto_compute_fairshare_institute)

logger = logging.getLogger(__name__)

# Environment variables for auto_compute_allocation in tasks.py
AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION = import_from_settings('AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION')

# automatically create a compute allocation, called by project_new signal
def add_auto_compute_allocation(project_obj):
    """ Method to add a compute allocation automatically upon project creation - uses signals for project creation """

    project_code = project_obj.project_code
    auto_allocation_clusters = get_cluster_resources_tuple()

    try:
        # create the allocation and return it
        allocation_obj = allocation_auto_compute(project_obj, project_code)

        # add all clusters in the tuple, which might just be 1x
        allocation_obj.resources.add(* auto_allocation_clusters)

        # allocation user - PI
        allocation_auto_compute_pi(project_obj, allocation_obj)

        # slurm account name using PROJECT_CODE
        allocation_attribute_type_obj_slurm_account_name = AllocationAttributeType.objects.get(name='slurm_account_name')

        # add the slurm account name
        allocation_auto_compute_slurm(allocation_attribute_type_obj_slurm_account_name, allocation_obj, project_code)

        # add slurm user specs
        fairshare_value="Fairshare=parent"
        allocation_attribute_type_obj_slurm_user_specs = AllocationAttributeType.objects.get(name='slurm_user_specs')
        allocation_auto_compute_fairshare(allocation_attribute_type_obj_slurm_user_specs, allocation_obj, fairshare_value)
    except:
        logger.error("Failed to add auto_compute_allocation")

    # finally if enabled add the institution based fairshare
    if AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION:
        allocation_auto_compute_fairshare_institute(project_obj, allocation_obj, project_code)