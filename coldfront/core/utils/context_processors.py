from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date

from django.conf import settings

import logging


logger = logging.getLogger(__name__)


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
