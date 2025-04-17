import logging
import datetime

from coldfront.core.utils.common import import_from_settings

from coldfront.core.allocation.models import (Allocation,
                                             AllocationAttribute,
                                             AllocationAttributeType,
                                             AllocationStatusChoice,
                                             AllocationUser,
                                             AllocationUserStatusChoice)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource, ResourceType

# Environment variables for auto_compute_allocation in utils.py
AUTO_COMPUTE_ALLOCATION_END_DELTA = import_from_settings('AUTO_COMPUTE_ALLOCATION_END_DELTA')
AUTO_COMPUTE_ALLOCATION_CHANGABLE = import_from_settings('AUTO_COMPUTE_ALLOCATION_CHANGABLE')
AUTO_COMPUTE_ALLOCATION_LOCKED = import_from_settings('AUTO_COMPUTE_ALLOCATION_LOCKED')

# import dependent var, N.B. default is empty dict
PROJECT_INSTITUTION_EMAIL_MAP = import_from_settings('PROJECT_INSTITUTION_EMAIL_MAP')

logger = logging.getLogger(__name__)

def get_cluster_resources_tuple():
    # find 'Cluster' within ResourceType
    cluster_pk_value=ResourceType.objects.get(name='Cluster').pk
    # filter for clusters
    resource_queryset=Resource.objects.filter(resource_type=cluster_pk_value)

    # initialise a list which will store all clusters - even if just 1x
    cluster_list=[]
    # get cluster resource instance(s)
    for a_cluster in resource_queryset:
        cluster_list.append(a_cluster.pk)

    auto_allocation_clusters=tuple(cluster_list)

    return auto_allocation_clusters

# create the allocation
def allocation_auto_compute(project_obj, project_code):
    allocation_end_date = datetime.date.today() + datetime.timedelta(days=AUTO_COMPUTE_ALLOCATION_END_DELTA)

    allocation_status_obj = AllocationStatusChoice.objects.get(name='New')  # alternative is Active
    allocation_description = str(f"auto:Cluster:{project_code}")

    allocation_obj = Allocation.objects.create(
        project=project_obj,
        justification='System automatically created compute allocation',
        description=allocation_description,
        status=allocation_status_obj,
        quantity=1,
        start_date=datetime.date.today(),
        end_date=allocation_end_date,
        is_locked=AUTO_COMPUTE_ALLOCATION_LOCKED,  # admin needs to unlock to permit changes
        is_changeable=AUTO_COMPUTE_ALLOCATION_CHANGABLE)  # no ability to request change to this allocation

    return allocation_obj

# adding pi to allocation, not other users, as they won't exist on project creation
def allocation_auto_compute_pi(project_obj, allocation_obj):
    allocation_user_obj = AllocationUser.objects.create(
        allocation=allocation_obj,
        user=project_obj.pi,
        status=AllocationUserStatusChoice.objects.get(name='Active')
    )
    return allocation_user_obj

# for slurm account
def allocation_auto_compute_slurm(allocation_attribute_type_obj, allocation_obj, project_code):
    allocation_attribute_obj = AllocationAttribute.objects.create(
        allocation=allocation_obj,
        allocation_attribute_type=allocation_attribute_type_obj,
        value=str(project_code)
    )
    return allocation_attribute_obj

# for slurm fairshare parent user_specs
def allocation_auto_compute_fairshare(allocation_attribute_type_obj, allocation_obj, fairshare_value):
    allocation_attribute_obj = AllocationAttribute.objects.create(
        allocation=allocation_obj,
        allocation_attribute_type=allocation_attribute_type_obj,
        value=fairshare_value
    )
    return allocation_attribute_obj

# slurm specs when fairshare institution is enabled, test for pre-reqs first
def allocation_auto_compute_fairshare_institute(project_obj, allocation_obj, project_code):
    if not PROJECT_INSTITUTION_EMAIL_MAP:
        logger.error("PROJECT_INSTITUTION_EMAIL_MAP must be in valid dictionary format")
        return None

    fairshare_institution = project_obj.institution

    if fairshare_institution != "None":

        allocation_attribute_type_obj = AllocationAttributeType.objects.get(name='slurm_specs')
        fairshare_value = f"Fairshare={fairshare_institution}"

        allocation_attribute_obj = AllocationAttribute.objects.create(
            allocation=allocation_obj,
            allocation_attribute_type=allocation_attribute_type_obj,
            value=fairshare_value
        )

    else:
        logger.info(f"Project with {project_code} has institution value of None. Can't add a slurm fairshare attribute based on institution.")