import logging
import pytz

from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.statistics.models import Job
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime


def set_job_amount(jobslurmid, amount, update_usages=True):
    """Set the number of service units for the Job with the given Slurm
    ID to the given amount. Optionally update associated usages.

    Parameters:
        - jobslurmid (str)
        - amount (Decimal)

    Returns:
        - None

    Raises:

    """
    assert isinstance(jobslurmid, str)
    assert isinstance(amount, Decimal)

    with transaction.atomic():
        job = Job.objects.select_for_update().get(jobslurmid=jobslurmid)

        if update_usages:
            account = job.accountid
            user = job.userid
            allocation_objects = get_accounting_allocation_objects(
                account, user=user)

            account_usage = (
                AllocationAttributeUsage.objects.select_for_update().get(
                    pk=allocation_objects.allocation_attribute_usage.pk))
            user_account_usage = (
                AllocationUserAttributeUsage.objects.select_for_update().get(
                    pk=allocation_objects.allocation_user_attribute_usage.pk))

            difference = amount - job.amount

            new_account_usage = max(
                account_usage.value + difference, Decimal('0.00'))
            account_usage.value = new_account_usage
            account_usage.save()

            new_user_account_usage = max(
                user_account_usage.value + difference, Decimal('0.00'))
            user_account_usage.value = new_user_account_usage
            user_account_usage.save()

        # Do not update the job.amount before calculating the difference.
        job.amount = amount
        job.save()


def validate_job_dates(job_data, allocation, end_date_expected=False):
    """Given a dictionary representing a Job, its corresponding
    Allocation, and whether the Job is expected to include an end date,
    return whether:
        (a) The Job has the expected dates,
        (b) The Job's corresponding Allocation has the expected dates,
            and
        (c) The Job started and ended within the Allocation's dates.

    Write errors or warnings to the log if not."""
    logger = logging.getLogger(__name__)

    date_format = '%Y-%m-%d %H:%M:%SZ'

    jobslurmid = job_data['jobslurmid']
    account_name = job_data['accountid'].name

    # The Job should have submit, start, and, if applicable, end dates.
    expected_date_keys = ['submitdate', 'startdate']
    if end_date_expected:
        expected_date_keys.append('enddate')
    expected_dates = {
        key: job_data.get(key, None) for key in expected_date_keys}
    for key, expected_date in expected_dates.items():
        if not isinstance(expected_date, datetime):
            logger.error(f'Job {jobslurmid} does not have a {key}.')
            return False

    # The Job's corresponding Allocation should have a start date.
    allocation_start_date = allocation.start_date
    if not isinstance(allocation_start_date, date):
        logger.error(
            f'Allocation {allocation.pk} (Project {account_name}) does not '
            f'have a start date.')
        return False

    # The Job should not have started before its corresponding Allocation's
    # start date.
    job_start_dt_utc = expected_dates['startdate']
    allocation_start_dt_utc = display_time_zone_date_to_utc_datetime(
        allocation_start_date)
    if job_start_dt_utc < allocation_start_dt_utc:
        logger.warning(
            f'Job {jobslurmid} start date '
            f'({job_start_dt_utc.strftime(date_format)}) is before Allocation '
            f'{allocation.pk} (Project {account_name}) start date '
            f'({allocation_start_dt_utc.strftime(date_format)}).')
        return False

    if not end_date_expected:
        return True

    # The Job's corresponding Allocation may have an end date. (Compare
    # against the maximum date if not.)
    computing_allowance_interface = ComputingAllowanceInterface()
    periodic_project_name_prefixes = tuple([
        computing_allowance_interface.code_from_name(allowance.name)
        for allowance in computing_allowance_interface.allowances()
        if ComputingAllowance(allowance).is_periodic()])
    if account_name.startswith(periodic_project_name_prefixes):
        allocation_end_date = allocation.end_date
        if not isinstance(allocation_end_date, date):
            logger.error(
                f'Allocation {allocation.pk} (Project {account_name}) does not '
                f'have an end date.')
            return False
        allocation_end_dt_utc = (
            display_time_zone_date_to_utc_datetime(allocation_end_date) +
            timedelta(hours=24) -
            timedelta(microseconds=1))
    else:
        allocation_end_dt_utc = datetime.max.replace(tzinfo=pytz.utc)

    # The Job should not have ended after the last microsecond of its
    # corresponding Allocation's end date.
    job_end_dt_utc = expected_dates['enddate']
    if job_end_dt_utc > allocation_end_dt_utc:
        logger.warning(
            f'Job {jobslurmid} end date '
            f'({job_end_dt_utc.strftime(date_format)}) is after Allocation '
            f'{allocation.pk} (Project {account_name}) end date '
            f'({allocation_end_dt_utc.strftime(date_format)}).')
        return False

    return True
