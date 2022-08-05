import logging

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

        for status in ['Pending - Add', 'Processing', 'Active', 'Denied']:
            count = 0
            attributes = \
                AllocationUserAttribute.objects.filter(
                    allocation_attribute_type=cluster_account_status,
                    value=status)

            status_choice = \
                ClusterAccessRequestStatusChoice.objects.get(name=status)

            for attr in attributes.iterator():
                user = attr.allocation_user.user

                request, created = ClusterAccessRequest.objects.get_or_create(
                    allocation_user=attr.allocation_user,
                    status=status_choice,
                    request_time=attr.created,
                    host_user=user.userprofile.host_user,
                    billing_activity=user.userprofile.billing_activity)

                if created:
                    count += 1

                if status in ['Active', 'Denied']:
                    request.completion_time = attr.modified
                    request.save()

            message = f'Created {count} new {status} ClusterAccessRequests.'
            self.stdout.write(self.style.SUCCESS(message))
