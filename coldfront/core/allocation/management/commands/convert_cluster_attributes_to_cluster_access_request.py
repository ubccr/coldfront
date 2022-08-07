from collections import Counter
from datetime import datetime
import logging

from django.core.management import BaseCommand

from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute, ClusterAccessRequestStatusChoice, \
    ClusterAccessRequest
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime


"""An admin command that creates ClusterAccessRequest objects for
existing AllocationUserAttribute objects with type 'Cluster Account
Status'."""


class Command(BaseCommand):

    help = (
        'Create ClusterAccessRequest objects for existing '
        'AllocationUserAttribute objects with type \'Cluster Account '
        'Status\', optionally filtering for those created on or after the '
        'given date.')

    logger = logging.getLogger(__name__)

    date_format = '%Y-%m-%d'

    def add_arguments(self, parser):
        parser.add_argument(
            '--created_after',
            help=(
                f'A date (YYYY-MM-DD) that filters attributes to include only '
                f'those created on or after it.'),
            type=str)

    def handle(self, *args, **options):
        created_after = options.get('created_after', '1970-01-01')
        created_after_utc_dt = display_time_zone_date_to_utc_datetime(
            datetime.strptime(created_after, self.date_format).date())

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        attribute_value_to_request_status = {
            'Pending - Add': ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            'Processing': ClusterAccessRequestStatusChoice.objects.get(
                name='Processing'),
            'Active': ClusterAccessRequestStatusChoice.objects.get(
                name='Complete'),
            'Denied': ClusterAccessRequestStatusChoice.objects.get(
                name='Denied'),
        }

        allocation_user_attributes = \
            AllocationUserAttribute.objects.prefetch_related(
                'history'
            ).filter(
                allocation_attribute_type=cluster_account_status,
                value__in=attribute_value_to_request_status.keys()
            ).order_by('id')

        num_created_by_request_status_name = Counter()

        for attribute in allocation_user_attributes.iterator():
            # Find all changes to the attribute on or after the filter date, in
            # ascending order.
            sorted_historical_attributes = list(
                attribute.history.filter(
                    history_date__gte=created_after_utc_dt
                ).order_by('history_id'))
            if not sorted_historical_attributes:
                continue
            latest_pending_add_dt, latest_active_dt = None, None
            for historical_attribute in sorted_historical_attributes:
                attribute_value = historical_attribute.value

                # The attribute may initially have been created with no value.
                if not attribute_value:
                    continue

                request_status = attribute_value_to_request_status[
                    attribute_value]
                created = False
                if attribute_value == 'Pending - Add':
                    # The attribute value being changed to 'Pending - Add'
                    # indicates the start of a new request flow.
                    latest_pending_add_dt = historical_attribute.history_date
                elif attribute_value == 'Active':
                    # The attribute value being changed to 'Active' when it was
                    # previously 'Pending - Add' indicates that that request
                    # flow was completed.
                    latest_active_dt = historical_attribute.history_date
                    if not latest_pending_add_dt:
                        continue
                    _, created = self.update_or_create_request(
                        historical_attribute, request_status,
                        latest_pending_add_dt,
                        completion_time=historical_attribute.history_date)
                elif attribute_value == 'Denied':
                    # The attribute value being changed to 'Denied' when it was
                    # previously 'Pending - Add', without having changed to
                    # 'Active' in between, indicates that that request flow was
                    # denied. The additional check is necessary because the
                    # value may have been changed to 'Denied' as a result of
                    # the User being removed from the corresponding Project.
                    if not latest_pending_add_dt:
                        continue
                    if (latest_active_dt and
                            latest_active_dt > latest_pending_add_dt):
                        continue
                    _, created = self.update_or_create_request(
                        historical_attribute, request_status,
                        latest_pending_add_dt,
                        completion_time=historical_attribute.history_date)

                num_created_by_request_status_name[request_status.name] += int(
                    created)

            # If the last historical attribute has 'Pending - Add' or
            # 'Processing' status, create a corresponding request.
            latest_historical_attribute = sorted_historical_attributes[-1]
            if latest_historical_attribute.value in (
                    'Pending - Add', 'Processing'):
                request_status = attribute_value_to_request_status[
                    latest_historical_attribute.value]
                _, created = self.update_or_create_request(
                    latest_historical_attribute, request_status,
                    # The attribute should have had a 'Pending - Add' status
                    # prior to this.
                    latest_pending_add_dt, latest_historical_attribute.value)
                num_created_by_request_status_name[request_status.name] += int(
                    created)

        for request_status_name, num_created in \
                num_created_by_request_status_name.items():
            message = (
                f'Created {num_created} ClusterAccessRequests with status '
                f'\'{request_status_name}\'.')
            self.logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))

    @staticmethod
    def update_or_create_request(historical_allocation_user_attribute, status,
                                 request_time, completion_time=None):
        """Update or create a ClusterAccessRequest for the given
        HistoricalAllocationUserAttribute. Set the status to the given
        one, along with other fields. Return the request and whether it
        was just created."""
        allocation_user = historical_allocation_user_attribute.allocation_user
        user_profile = allocation_user.user.userprofile

        defaults = {
            'status': status,
            'host_user': user_profile.host_user,
            'billing_activity': user_profile.billing_activity,
        }
        if isinstance(completion_time, datetime):
            defaults['completion_time'] = completion_time

        # If a request with this AllocationUser and request time already
        # exists, avoid creating another one. (It is highly unlikely for a User
        # to have multiple changes for the same attribute at exactly the same
        # time.)
        return ClusterAccessRequest.objects.update_or_create(
            allocation_user=allocation_user,
            request_time=request_time,
            defaults=defaults)
