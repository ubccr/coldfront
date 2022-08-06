import logging
from datetime import datetime, timezone

from django.core.management import BaseCommand

from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute, ClusterAccessRequestStatusChoice, \
    ClusterAccessRequest


"""An admin command that converts AllocationUserAttribute objects with type 
Cluster Account Status to the new ClusterAccessRequest model."""


class Command(BaseCommand):

    help = (
        'Converts AllocationUserAttribute objects with type Cluster'
        'Account Status to the new ClusterAccessRequest model.')

    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """
        Converts AllocationUserAttribute objects with type Cluster
        Account Status to the new ClusterAccessRequest model.
        """

        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')

        for status in ['Pending - Add', 'Processing', 'Complete', 'Denied']:
            count = 0
            attributes = \
                AllocationUserAttribute.objects.filter(
                    allocation_attribute_type=cluster_account_status,
                    value=status)

            status_choice = \
                ClusterAccessRequestStatusChoice.objects.get(name=status)

            portal_launch = datetime(2021, 6, 1, tzinfo=timezone.utc)
            for attr in attributes.iterator():
                # Only make requests for AllocationUserAttributes created
                # after the portal's launch.
                if attr.created >= portal_launch:
                    user = attr.allocation_user.user

                    request, created = ClusterAccessRequest.objects.get_or_create(
                        allocation_user=attr.allocation_user,
                        status=status_choice,
                        request_time=attr.created,
                        host_user=user.userprofile.host_user,
                        billing_activity=user.userprofile.billing_activity)

                    if created:
                        count += 1

                    if status in ['Complete', 'Denied']:
                        request.completion_time = attr.modified
                        request.save()

            message = f'Created {count} new {status} ClusterAccessRequests.'
            self.stdout.write(self.style.SUCCESS(message))
