from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period

from constance import config
from django.conf import settings
from django.db.models import Q

import logging


logger = logging.getLogger(__name__)


def allocation_navbar_visibility(request):
    """Set the following context variables:
        - ALLOCATION_VISIBLE: Whether the allocation tab should be
          visible to the requesting user."""
    allocation_key = 'ALLOCATION_VISIBLE'
    context = {
        allocation_key: False,
    }

    if not request.user.is_authenticated:
        return context

    # Allocation list view should be visible to superusers and staff.
    if request.user.is_superuser or request.user.is_staff:
        context[allocation_key] = True
        return context

    # Allocation list view should be visible to active PIs and Managers.
    project_user = ProjectUser.objects.filter(
        Q(role__name__in=['Manager', 'Principal Investigator']) &
        Q(status__name='Active') &
        Q(user=request.user))
    context[allocation_key] = project_user.exists()

    return context


def constance_config(request):
    return {'CONSTANCE_CONFIG': config}


def current_allowance_year_allocation_period(request):
    context = {}
    try:
        allocation_period = get_current_allowance_year_period()
    except Exception as e:
        message = (
            f'Failed to retrieve current Allowance Year AllocationPeriod. '
            f'Details:\n'
            f'{e}')
        logger.exception(message)
    else:
        context['CURRENT_ALLOWANCE_YEAR_ALLOCATION_PERIOD'] = allocation_period
    return context


def display_time_zone(request):
    return {'DISPLAY_TIME_ZONE': settings.DISPLAY_TIME_ZONE}


def portal_and_program_names(request):
    return {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'PROGRAM_NAME_LONG': settings.PROGRAM_NAME_LONG,
        'PROGRAM_NAME_SHORT': settings.PROGRAM_NAME_SHORT,
    }
