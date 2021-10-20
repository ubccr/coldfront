from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import SavioProjectAllocationRequest
from django.dispatch import receiver
from django.dispatch import Signal
# Imported without 'from' to avoid a circular import.
import coldfront.core.project.utils_.renewal_utils as renewal_utils
import logging


logger = logging.getLogger(__name__)


# A signal to send when a SavioProjectAllocationRequest is denied.
new_project_request_denied = Signal()


@receiver(new_project_request_denied)
def deny_associated_allocation_renewal_request(sender, **kwargs):
    """When a SavioProjectAllocationRequest is denied, if it is
    referenced by an AllocationRenewalRequest, also deny that
    request.

    Parameters:
        - sender: None
        - **kwargs
            - request_id (int): The ID of the denied request
    """
    request_id = kwargs['request_id']
    try:
        new_project_request_obj = SavioProjectAllocationRequest.objects.get(
            id=request_id)
    except SavioProjectAllocationRequest.DoesNotExist:
        message = f'Invalid SavioProjectAllocationRequest ID {request_id}.'
        logger.error(message)
        return

    try:
        renewal_request_obj = AllocationRenewalRequest.objects.get(
            new_project_request=new_project_request_obj)
    except AllocationRenewalRequest.DoesNotExist:
        return
    except AllocationRenewalRequest.MultipleObjectsReturned:
        message = (
            f'Unexpectedly found multiple AllocationRenewalRequests that '
            f'reference SavioProjectAllocationRequest {request_id}.')
        logger.error(message)
        return

    try:
        runner = renewal_utils.AllocationRenewalDenialRunner(
            renewal_request_obj)
        runner.run()
    except Exception as e:
        message = (
            f'Encountered unexpected exception when automatically denying '
            f'AllocationRenewalRequest {renewal_request_obj.pk} after '
            f'SavioProjectAllocationRequest {request_id} was denied. '
            f'Details:')
        logger.error(message)
        logger.exception(e)
        return

    message = (
        f'Automatically denied AllocationRenewalRequest '
        f'{renewal_request_obj.pk} after SavioProjectAllocationRequest '
        f'{request_id} was denied.')
    logger.info(message)
