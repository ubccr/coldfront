import logging
import pytz

from collections import OrderedDict
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from coldfront.api.permissions import IsAdminUserOrReadOnly
from coldfront.api.statistics.pagination import JobPagination
from coldfront.api.statistics.serializers import JobSerializer
from coldfront.api.statistics.utils import convert_utc_datetime_to_unix_timestamp
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils import get_computing_allowance_project_prefixes
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime


DATE_FORMAT = '%Y-%m-%d %H:%M:%SZ'


authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)

user_parameter = openapi.Parameter(
    'user',
    openapi.IN_QUERY,
    description='The cluster username of the user who submitted the job.',
    type=openapi.TYPE_STRING)

account_parameter = openapi.Parameter(
    'account',
    openapi.IN_QUERY,
    description='The name of the account under which the job was submitted.',
    type=openapi.TYPE_STRING)

jobstatus_parameter = openapi.Parameter(
    'jobstatus',
    openapi.IN_QUERY,
    description='The status of the job.',
    type=openapi.TYPE_STRING)

max_amount_parameter = openapi.Parameter(
    'max_amount',
    openapi.IN_QUERY,
    description='The maximum number of service units used by the job.',
    type=openapi.TYPE_NUMBER)

min_amount_parameter = openapi.Parameter(
    'min_amount',
    openapi.IN_QUERY,
    description='The minimum number of service units used by the job.',
    type=openapi.TYPE_NUMBER)

partition_parameter = openapi.Parameter(
    'partition',
    openapi.IN_QUERY,
    description='The partition on which the job ran.',
    type=openapi.TYPE_STRING)

start_time_parameter = openapi.Parameter(
    'start_time',
    openapi.IN_QUERY,
    description=(
        'A starting time as a Unix timestamp: only jobs ending at or after '
        'this time are included.'),
    type=openapi.TYPE_NUMBER)

end_time_parameter = openapi.Parameter(
    'end_time',
    openapi.IN_QUERY,
    description=(
        'An ending time as a Unix timestamp: only jobs ending before or at '
        'this time are included.'),
    type=openapi.TYPE_NUMBER)


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        manual_parameters=[
            user_parameter, account_parameter, jobstatus_parameter,
            max_amount_parameter, min_amount_parameter, partition_parameter,
            start_time_parameter, end_time_parameter],
        operation_description=(
            'Returns jobs, with optional filtering by user, account, '
            'job status, amount, partition, and end date.')))
class JobViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                 mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                 viewsets.GenericViewSet):
    """A ViewSet for the Job model, intended for allocation accounting
    purposes."""

    pagination_class = JobPagination
    permission_classes = [IsAdminUserOrReadOnly]
    serializer_class = JobSerializer

    def get_queryset(self):
        # Begin with all jobs.
        jobs = Job.objects.all()
        if self.action == 'list':
            # Filter by user, if provided.
            username = self.request.query_params.get('user', None)
            if username:
                user = User.objects.get(username=username)
                if user:
                    jobs = jobs.filter(userid=user)
                else:
                    jobs = Job.objects.none()

            # Filter by account, if provided.
            account_name = self.request.query_params.get('account', None)
            if account_name:
                try:
                    account = Project.objects.get(name=account_name)
                except Project.DoesNotExist:
                    jobs = Job.objects.none()
                else:
                    jobs = jobs.filter(accountid=account)

            # Filter by jobstatus, if provided.
            jobstatus = self.request.query_params.get('jobstatus', None)
            if jobstatus:
                jobs = jobs.filter(jobstatus=jobstatus)

            # Filter by amount minimum and/or maximum, if provided.
            min_amount = self.request.query_params.get(
                'min_amount', settings.ALLOCATION_MIN)
            if min_amount:
                try:
                    min_amount = Decimal(min_amount)
                except InvalidOperation as e:
                    raise serializers.ValidationError(
                        f'Invalid minimum amount {min_amount}. Details: {e}')
            max_amount = self.request.query_params.get(
                'max_amount', settings.ALLOCATION_MAX)
            if max_amount:
                try:
                    max_amount = Decimal(max_amount)
                except InvalidOperation as e:
                    raise serializers.ValidationError(
                        f'Invalid maximum amount {max_amount}. Details: {e}')
            jobs = jobs.filter(amount__gte=min_amount, amount__lte=max_amount)

            # Filter by partition, if provided.
            partition = self.request.query_params.get('partition', None)
            if partition:
                jobs = jobs.filter(partition=partition)

            # Retrieve the default allocation year start and end as Unix
            # timestamps.
            try:
                current_allowance_year_period = \
                    get_current_allowance_year_period()
                default_start = display_time_zone_date_to_utc_datetime(
                    current_allowance_year_period.start_date)
                default_end = (
                    display_time_zone_date_to_utc_datetime(
                        current_allowance_year_period.end_date) +
                    timedelta(hours=24) -
                    timedelta(microseconds=1))
            except Exception as e:
                raise serializers.ValidationError(
                    f'Failed to retrieve default start and end times. '
                    f'Details: {e}')
            default_start_time = convert_utc_datetime_to_unix_timestamp(
                default_start)
            default_end_time = convert_utc_datetime_to_unix_timestamp(
                default_end)

            # Use the user-provided times if provided, or the defaults.
            start_time = self.request.query_params.get(
                'start_time', default_start_time)
            end_time = self.request.query_params.get(
                'end_time', default_end_time)

            # Convert Unix timestamps to UTC datetimes.
            try:
                start_time = datetime.utcfromtimestamp(
                    float(start_time)).replace(tzinfo=pytz.utc)
            except (TypeError, ValueError) as e:
                raise serializers.ValidationError(
                    f'Invalid starting timestamp {start_time}. Details: {e}')
            try:
                end_time = datetime.utcfromtimestamp(
                    float(end_time)).replace(tzinfo=pytz.utc)
            except (TypeError, ValueError) as e:
                raise serializers.ValidationError(
                    f'Invalid ending timestamp {start_time}. Details: {e}')

            # Filter on submitdate, keeping those that end between the given
            # times, inclusive.
            jobs = jobs.filter(
                submitdate__gte=start_time, submitdate__lte=end_time)

        # Return filtered jobs in ascending submitdate order.
        return jobs.order_by('submitdate')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
            'Creates a new Job identified by the given Slurm ID.'))
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """The method for POST (create) requests."""
        logger = logging.getLogger(__name__)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # These must exist because they are verified in JobSerializer.validate,
        # part of this atomic block.
        jobslurmid = serializer.validated_data['jobslurmid']
        user = serializer.validated_data['userid']
        account = serializer.validated_data['accountid']
        allocation_objects = get_accounting_allocation_objects(
            account, user=user)
        account_allocation = Decimal(
            allocation_objects.allocation_attribute.value)
        user_account_allocation = Decimal(
            allocation_objects.allocation_user_attribute.value)
        account_usage = (
            AllocationAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_attribute_usage.pk))
        user_account_usage = (
            AllocationUserAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_user_attribute_usage.pk))

        logger.info(
            f'New Job POST request with data: {serializer.validated_data}.')

        job_has_amount = 'amount' in serializer.validated_data
        if not job_has_amount:
            logger.warning(f'Job {jobslurmid} has no amount.')

        try:
            job_dates_valid = self.validate_job_dates(
                serializer.validated_data, allocation_objects.allocation,
                end_date_expected=False)
        except Exception as e:
            job_dates_valid = False
            logger.exception(
                f'Failed to determine whether dates for Job {jobslurmid} are '
                f'valid. Details:\n'
                f'{e}')

        # If an amount is specified, and job dates are valid, update usages.
        if job_has_amount and job_dates_valid:
            amount = Decimal(serializer.validated_data['amount'])

            # Because of Slurm limitations, 'can_submit_job' and 'create' are
            # called separately. As a result, it is possible to submit several
            # jobs at the same time that individually pass 'can_submit_job',
            # placing them in the Slurm queue, but that overdraw allocations
            # when their costs are summed. Once in the Slurm queue, 'create'
            # must be called for each, since the Job is valid in the Slurm
            # database. Therefore, overdrawing is permitted here.

            new_account_usage = account_usage.value + amount
            if new_account_usage > account_allocation:
                message = (
                    f'Project {account.name} allocation will be overdrawn. '
                    f'Allocation: {account_allocation}. Current usage: '
                    f'{account_usage.value}. Requested job amount: {amount}. '
                    f'This is permitted by design.')
                logger.error(message)
            logger.info(
                f'Setting usage for Project {account.name} to '
                f'{new_account_usage}.')
            account_usage.value = new_account_usage
            account_usage.save()

            new_user_account_usage = user_account_usage.value + amount
            if new_user_account_usage > user_account_allocation:
                message = (
                    f'User {user} allocation for Project {account.name} will '
                    f'be overdrawn. Allocation: {user_account_allocation}. '
                    f'Current usage: {user_account_usage.value}. Requested '
                    f'job amount: {amount}. This is permitted by design.')
                logger.error(message)
            logger.info(
                f'Setting usage for User {user} and Project {account.name} to '
                f'{user_account_usage.value} + {amount} = '
                f'{new_user_account_usage}.')
            user_account_usage.value = new_user_account_usage
            user_account_usage.save()
        else:
            logger.warning(f'Skipping usage updates for Job {jobslurmid}.')

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
            'Updates one or more fields of the Job identified by the given '
            'Slurm ID. This method is not supported.'),
        auto_schema=None)
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """The method for PATCH (partial update) requests."""
        return Response({'failure': 'This method is not supported.'})

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
            'Updates all fields of the Job identified by the given Slurm ID.'))
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """The method for PUT (update) requests."""
        logger = logging.getLogger(__name__)

        partial = kwargs.pop('partial', False)
        try:
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
        except Http404:
            instance = None
            serializer = self.get_serializer(
                data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # These must exist because they are verified in JobSerializer.validate,
        # part of this atomic block.
        jobslurmid = serializer.validated_data['jobslurmid']
        user = serializer.validated_data['userid']
        account = serializer.validated_data['accountid']
        allocation_objects = get_accounting_allocation_objects(
            account, user=user)
        account_usage = (
            AllocationAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_attribute_usage.pk))
        user_account_usage = (
            AllocationUserAttributeUsage.objects.select_for_update().get(
                pk=allocation_objects.allocation_user_attribute_usage.pk))

        logger.info(
            f'New Job PUT request with data: {serializer.validated_data}.')

        job_has_amount = 'amount' in serializer.validated_data
        if not job_has_amount:
            logger.warning(f'Job {jobslurmid} has no amount.')

        try:
            job_dates_valid = self.validate_job_dates(
                serializer.validated_data, allocation_objects.allocation,
                end_date_expected=True)
        except Exception as e:
            job_dates_valid = False
            logger.exception(
                f'Failed to determine whether dates for Job {jobslurmid} are '
                f'valid. Details:\n'
                f'{e}')

        # If an amount is specified and job dates are valid, update usages.
        if job_has_amount and job_dates_valid:
            amount = Decimal(serializer.validated_data['amount'])
            try:
                job = Job.objects.get(jobslurmid=jobslurmid)
            except Job.DoesNotExist:
                logger.info(
                    f'No Job with jobslurmid {jobslurmid} yet exists. '
                    f'Creating it.')
                new_account_usage = account_usage.value + amount
                logger.info(
                    f'Setting usage for Project {account.name} to '
                    f'{account_usage.value} + {amount} = {new_account_usage}.')
                account_usage.value = new_account_usage
                new_user_account_usage = user_account_usage.value + amount
                logger.info(
                    f'Setting usage for User {user} and Project '
                    f'{account.name} to {user_account_usage.value} + {amount} '
                    f'= {new_user_account_usage}.')
                user_account_usage.value = new_user_account_usage
            else:
                logger.info(
                    f'A Job with jobslurmid {jobslurmid} already exists. '
                    f'Updating it.')
                # The difference should be non-positive because the estimated
                # cost is an upper bound of the actual cost.
                difference = amount - job.amount
                new_account_usage = max(
                    account_usage.value + difference, Decimal('0.00'))
                logger.info(
                    f'Setting usage for Project {account.name} to max('
                    f'{account_usage.value} + ({amount} - {job.amount}), 0) = '
                    f'{new_account_usage}.')
                account_usage.value = new_account_usage
                new_user_account_usage = max(
                    user_account_usage.value + difference, Decimal('0.00'))
                logger.info(
                    f'Setting usage for User {user} and Project '
                    f'{account.name} to max({user_account_usage.value} + '
                    f'({amount} - {job.amount}), 0) = '
                    f'{new_user_account_usage}.')
                user_account_usage.value = new_user_account_usage
            account_usage.save()
            user_account_usage.save()
        else:
            logger.warning(f'Skipping usage updates for Job {jobslurmid}.')

        self.perform_update(serializer)

        if instance:
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need
                # to forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @staticmethod
    def validate_job_dates(job_data, allocation, end_date_expected=False):
        """Given a dictionary representing a Job, its corresponding
        Allocation, and whether the Job is expected to include an end
        date, return whether:
            (a) The Job has the expected dates,
            (b) The Job's corresponding Allocation has the expected
                dates, and
            (c) The Job started and ended within the Allocation's dates.

        Write errors or warnings to the log if not."""
        logger = logging.getLogger(__name__)

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
                f'Allocation {allocation.pk} (Project {account_name}) does '
                f'not have a start date.')
            return False

        # The Job should not have started before its corresponding Allocation's
        # start date.
        job_start_dt_utc = expected_dates['startdate']
        allocation_start_dt_utc = display_time_zone_date_to_utc_datetime(
            allocation_start_date)
        if job_start_dt_utc < allocation_start_dt_utc:
            logger.warning(
                f'Job {jobslurmid} start date '
                f'({job_start_dt_utc.strftime(DATE_FORMAT)}) is before '
                f'Allocation {allocation.pk} (Project {account_name}) start '
                f'date ({allocation_start_dt_utc.strftime(DATE_FORMAT)}).')
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
                    f'Allocation {allocation.pk} (Project {account_name}) '
                    f'does not have an end date.')
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
                f'({job_end_dt_utc.strftime(DATE_FORMAT)}) is after '
                f'Allocation {allocation.pk} (Project {account_name}) end '
                f'date ({allocation_end_dt_utc.strftime(DATE_FORMAT)}).')
            return False

        return True


job_cost_parameter = openapi.Parameter(
    'job_cost',
    openapi.IN_PATH,
    description=(
        f'A string representation of a nonnegative decimal number with no '
        f'greater than {settings.DECIMAL_MAX_DIGITS} total digits and no '
        f'greater than {settings.DECIMAL_MAX_PLACES} decimal places.'),
    type=openapi.TYPE_STRING)

user_id_parameter = openapi.Parameter(
    'user_id',
    openapi.IN_PATH,
    description=(
        'A string representation of the user\'s cluster UID, a five digit '
        'number.'),
    type=openapi.TYPE_STRING)

account_id_parameter = openapi.Parameter(
    'account_id',
    openapi.IN_PATH,
    description='The name of the account.',
    type=openapi.TYPE_STRING)

response_200 = openapi.Response(
    description=(
        f'A mapping from \'success\' to whether or not the job can be '
        f'submitted and a mapping from \'message\' to reasoning.'),
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties=OrderedDict((
            ('success', openapi.Schema(type=openapi.TYPE_BOOLEAN)),
            ('message', openapi.Schema(
                type=openapi.TYPE_STRING, x_nullable=True))))))

response_400 = openapi.Response(
    description=(
        f'A mapping from \'success\' to False and a mapping from \'message\' '
        f'to an error message.'),
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties=OrderedDict((
            ('success', openapi.Schema(
                type=openapi.TYPE_BOOLEAN, default=False)),
            ('message', openapi.Schema(
                type=openapi.TYPE_STRING, x_nullable=True))))))


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        job_cost_parameter, user_id_parameter, account_id_parameter,
        authorization_parameter],
    operation_description=(
        'Returns whether or not a Job with the given cost can be submitted by '
        'the given user for the given account.'),
    responses={
        200: response_200,
        400: response_400
    })
@api_view(['GET'])
@transaction.atomic
def can_submit_job(request, job_cost, user_id, account_id):
    """Given a Job cost, return True if adding it to the given user's
    usage would not exceed his or her allocation and adding it to the
    given account's usage would not exceed its allocation else False. If
    the ALLOW_ALL_JOBS setting is set to True, skip all checks and
    simply return True.

    Parameters:
        - request (HttpRequest): the Django request object
        - job_cost (str): the cost of the job to be checked
        - user_id (str): the cluster UID of the user
        - account_id (str): the name of the account

    Returns:
        - JsonResponse mapping 'success' to a boolean and 'message' to
        an error message.

    Raises:
        - None
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f'New can_submit_job request with job_cost {job_cost}, user_id '
        f'{user_id}, and account_id {account_id}.')

    affirmative = JsonResponse(
        status=status.HTTP_200_OK,
        data={
            'success': True,
            'message': f'A job with job_cost {job_cost} can be submitted.'
        })

    def non_affirmative(data_message):
        """Return a JsonResponse with status 200 and data including
        'success' set to False and 'message' set to the given string."""
        return JsonResponse(
            status=status.HTTP_200_OK,
            data={
                'success': False,
                'message': data_message
            })

    def client_error(data_message):
        """Return a JsonResponse with status 400 and data including
        'success' set to False and 'message' set to the given string."""
        return JsonResponse(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                'success': False,
                'message': data_message
            })

    server_error = JsonResponse(
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        data={
            'success': False,
            'message': f'Unexpected server error.'
        })

    # If all jobs are allowed, bypass checks.
    if settings.ALLOW_ALL_JOBS:
        return affirmative

    # Validate types.
    job_cost = job_cost.strip()
    user_id = user_id.strip()
    account_id = account_id.strip()
    if not job_cost or not isinstance(job_cost, str):
        message = f'job_cost {job_cost} is not a nonempty string.'
        return client_error(message)
    if not user_id or not isinstance(user_id, str):
        message = f'user_id {user_id} is not a nonempty string.'
        return client_error(message)
    if not account_id or not isinstance(account_id, str):
        message = f'account_id {account_id} is not a nonempty string.'
        return client_error(message)

    # Validate job_cost.
    try:
        job_cost = Decimal(job_cost)
    except InvalidOperation as e:
        message = (
            f'Encountered exception {e} when converting job_cost {job_cost} '
            f'to a decimal.')
        return client_error(message)
    decimal_tuple = job_cost.as_tuple()
    if decimal_tuple.sign:
        message = f'job_cost {job_cost} is not nonnegative.'
        return client_error(message)
    if len(decimal_tuple.digits) > settings.DECIMAL_MAX_DIGITS:
        message = (
            f'job_cost {job_cost} has greater than '
            f'{settings.DECIMAL_MAX_DIGITS} digits.')
        return client_error(message)
    if abs(decimal_tuple.exponent) > settings.DECIMAL_MAX_PLACES:
        message = (
            f'job_cost {job_cost} has greater than '
            f'{settings.DECIMAL_MAX_PLACES} decimal places.')
        return client_error(message)

    # Validate user_id.
    try:
        user = UserProfile.objects.get(cluster_uid=user_id).user
    except UserProfile.DoesNotExist:
        message = f'No user exists with user_id {user_id}.'
        return client_error(message)

    # Validate account_id.
    try:
        account = Project.objects.get(name=account_id)
    except Project.DoesNotExist:
        message = f'No account exists with account_id {account_id}.'
        return client_error(message)

    # Allow all jobs for accounts that are not intended to have
    # computing allowances (e.g., departmental cluster-specific projects).
    computing_allowance_project_prefixes = \
        get_computing_allowance_project_prefixes()
    if not account.name.startswith(computing_allowance_project_prefixes):
        return affirmative

    # Validate that needed accounting objects exist.
    try:
        allocation_objects = get_accounting_allocation_objects(
            account, user=user)
    except ProjectUser.DoesNotExist:
        message = (
            f'User {user.username} is not a member of account {account.name}.')
        logger.error(message)
        return non_affirmative(message)
    except Allocation.DoesNotExist:
        message = f'Account {account.name} has no active compute allocation.'
        logger.error(message)
        return non_affirmative(message)
    except Allocation.MultipleObjectsReturned:
        logger.error(
            f'Account {account.name} has more than one active compute '
            f'allocation.')
        return server_error
    except AllocationUser.DoesNotExist:
        message = (
            f'User {user.username} is not an active member of the compute '
            f'allocation for account {account.name}.')
        logger.error(message)
        return non_affirmative(message)
    except (MultipleObjectsReturned, ObjectDoesNotExist) as e:
        logger.error(
            f'Failed to retrieve a required database object. Details: {e}')
        return server_error
    except TypeError as e:
        logger.error(f'Incorrect input type. Details: {e}')
        return server_error

    # Retrieve compute allocation values.
    account_allocation = Decimal(allocation_objects.allocation_attribute.value)
    user_account_allocation = Decimal(
        allocation_objects.allocation_user_attribute.value)

    # Retrieve compute usage values.
    account_usage = allocation_objects.allocation_attribute_usage.value
    user_account_usage = (
        allocation_objects.allocation_user_attribute_usage.value)

    # If the account has infinite service units, allow the job, regardless of
    # cost.
    computing_allowance = ComputingAllowance(
        ComputingAllowanceInterface().allowance_from_project(account))
    if computing_allowance.has_infinite_service_units():
        return affirmative

    # Return whether both usages would not exceed their respective allocations.
    if job_cost + account_usage > account_allocation:
        message = (
            f'Adding job_cost {job_cost} to account balance {account_usage} '
            f'would exceed account allocation {account_allocation}.')
        return non_affirmative(message)
    if job_cost + user_account_usage > user_account_allocation:
        message = (
            f'Adding job_cost {job_cost} to user balance {user_account_usage} '
            f'would exceed user allocation {user_account_allocation}.')
        return non_affirmative(message)

    return affirmative
