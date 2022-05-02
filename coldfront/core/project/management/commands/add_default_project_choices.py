import os

from django.core.management.base import BaseCommand

from coldfront.core.project.models import (ProjectReviewStatusChoice,
                                           ProjectStatusChoice,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectAllocationRequestStatusChoice,
                                           ProjectUserRemovalRequestStatusChoice)


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        # ProjectStatusChoice.objects.all().delete()
        for choice in ['New', 'Active', 'Archived', 'Denied', 'Inactive', ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        # ProjectReviewStatusChoice.objects.all().delete()
        for choice in ['Completed', 'Pending', ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        # ProjectUserRoleChoice.objects.all().delete()
        for choice in ['User', 'Manager', 'Principal Investigator', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        # ProjectUserStatusChoice.objects.all().delete()
        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        # ProjectAllocationRequestStatusChoice.objects.all().delete()
        choices = [
            'Under Review',
            'Approved - Processing',
            'Approved - Scheduled',
            'Approved - Complete',
            'Denied',
        ]
        for choice in choices:
            ProjectAllocationRequestStatusChoice.objects.get_or_create(
                name=choice)

        for choice in ['Pending', 'Processing', 'Complete']:
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(name=choice)
