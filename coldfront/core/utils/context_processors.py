from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.utils.common import display_time_zone_current_date

from django.conf import settings


def current_allowance_year_allocation_period(request):
    date = display_time_zone_current_date()
    allocation_periods = AllocationPeriod.objects.filter(
        name__startswith='Allowance Year',
        start_date__lte=date,
        end_date__gte=date).order_by('start_date')
    context = {}
    if allocation_periods.exists():
        context['CURRENT_ALLOWANCE_YEAR_ALLOCATION_PERIOD'] = \
            allocation_periods.first()
    return context


def display_time_zone(request):
    return {'DISPLAY_TIME_ZONE': settings.DISPLAY_TIME_ZONE}
