import logging

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.models import Project
from coldfront.core.resource.utils import get_computing_allowance_project_prefixes


logger = logging.getLogger(__name__)


def get_or_create_billing_activity_from_full_id(full_id):
    """Given a fully-formed billing ID, get or create a matching
    BillingActivity, creating a BillingProject as needed."""
    project_identifier, activity_identifier = full_id.split('-')
    billing_project, _ = BillingProject.objects.get_or_create(
        identifier=project_identifier)
    billing_activity, _ = BillingActivity.objects.get_or_create(
        billing_project=billing_project, identifier=activity_identifier)
    return billing_activity


def is_project_billing_id_required_and_missing(project_obj):
    """Return whether the given Project is expected to have a default
    billing ID, and, if so, whether it has one."""
    assert isinstance(project_obj, Project)
    if not flag_enabled('LRC_ONLY'):
        return False
    computing_allowance_project_prefixes = \
        get_computing_allowance_project_prefixes()
    if not project_obj.name.startswith(computing_allowance_project_prefixes):
        return False
    allocation = get_project_compute_allocation(project_obj)
    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Billing Activity')
    billing_attribute = allocation.allocationattribute_set.filter(
        allocation_attribute_type=allocation_attribute_type).first()
    if billing_attribute is None:
        return True
    try:
        billing_activity_pk = int(billing_attribute.value.strip())
        BillingActivity.objects.get(pk=billing_activity_pk)
    except Exception as e:
        logger.exception(e)
        return True
    return False
