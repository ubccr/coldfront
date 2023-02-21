from django.core.management.base import BaseCommand

from coldfront.core.project.models import (ProjectReviewStatusChoice,
                                           ProjectStatusChoice,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectTypeChoice)


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        ProjectStatusChoice.objects.all().delete()
        for choice in ['New', 'Active', 'Archived', 'Denied', 'Expired', 'Review Pending', 'Waiting For Admin Approval', ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        ProjectReviewStatusChoice.objects.all().delete()
        for choice in ['Approved', 'Pending', 'Denied', 'Completed', ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        ProjectUserRoleChoice.objects.all().delete()
        for choice in ['User', 'Manager', 'Group', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        ProjectUserStatusChoice.objects.all().delete()
        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        ProjectTypeChoice.objects.all().delete()
        for choice in ['Research', 'Class', ]:
            ProjectTypeChoice.objects.get_or_create(name=choice)
