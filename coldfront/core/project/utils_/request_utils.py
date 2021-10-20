from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from collections import namedtuple


def savio_request_denial_reason(savio_request):
    """Return the reason why the given SavioProjectAllocationRequest was
    denied, based on its 'state' field."""
    if not isinstance(savio_request, SavioProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(savio_request)}.')
    if savio_request.status.name != 'Denied':
        raise ValueError(
            f'Provided request has unexpected status '
            f'{savio_request.status.name}.')

    state = savio_request.state
    eligibility = state['eligibility']
    readiness = state['readiness']
    other = state['other']

    DenialReason = namedtuple(
        'DenialReason', 'category justification timestamp')

    if other['timestamp']:
        category = 'Other'
        justification = other['justification']
        timestamp = other['timestamp']
    elif eligibility['status'] == 'Denied':
        category = 'PI Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    elif readiness['status'] == 'Denied':
        category = 'Readiness Criteria Unsatisfied'
        justification = readiness['justification']
        timestamp = readiness['timestamp']
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)


def vector_request_denial_reason(vector_request):
    """Return the reason why the given VectorProjectAllocationRequest
    was denied, based on its 'state' field."""
    if not isinstance(vector_request, VectorProjectAllocationRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(vector_request)}.')
    if vector_request.status.name != 'Denied':
        raise ValueError(
            f'Provided request has unexpected status '
            f'{vector_request.status.name}.')

    state = vector_request.state
    eligibility = state['eligibility']

    DenialReason = namedtuple(
        'DenialReason', 'category justification timestamp')

    if eligibility['status'] == 'Denied':
        category = 'Requester Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)
