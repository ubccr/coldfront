from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.project.models import Project


def can_project_purchase_service_units(project):
    """Return whether the given Project is eligible to purchase
    additional Service Units for its allowance."""
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.name.startswith('ac_')


def has_pending_allocation_addition_request(project):
    """Return whether the given Project has an 'Under Review'
    AllocationAdditionRequest."""
    under_review_status = AllocationAdditionRequestStatusChoice.objects.get(
        name='Under Review')
    return AllocationAdditionRequest.objects.filter(
        project=project, status=under_review_status).exists()
