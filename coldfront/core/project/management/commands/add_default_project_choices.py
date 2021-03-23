import os

from django.core.management.base import BaseCommand

from coldfront.core.project.models import (ProjectReviewStatusChoice,
                                            ProjectStatusChoice,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            ProjectAllocationRequestStatusChoice)


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        ProjectStatusChoice.objects.all().delete()
        for choice in ['New', 'Active', 'Archived', ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        ProjectReviewStatusChoice.objects.all().delete()
        for choice in ['Completed', 'Pending', ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        ProjectUserRoleChoice.objects.all().delete()
        for choice in ['User', 'Manager', 'Principal Investigator', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        ProjectUserStatusChoice.objects.all().delete()
        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        ProjectAllocationRequestStatusChoice.objects.all().delete()
        for choice in ['Approved', 'Pending', 'Denied', ]:
            ProjectAllocationRequestStatusChoice.objects.get_or_create(
                name=choice)
