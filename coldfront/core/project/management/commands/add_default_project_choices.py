import os
from inspect import Attribute
from django.core.management.base import BaseCommand

from coldfront.core.project.models import (ProjectAttributeType,
                                            ProjectReviewStatusChoice,
                                            ProjectStatusChoice,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            ProjectTypeChoice,
                                            AttributeType)


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        ProjectStatusChoice.objects.all().delete()
        for choice in ['New', 'Active', 'Archived', 'Denied', 'Expired', 'Renewal Denied',
                       'Review Pending', 'Waiting For Admin Approval', 'Contacted By Admin', ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        ProjectReviewStatusChoice.objects.all().delete()
        for choice in ['Approved', 'Pending', 'Denied', 'Completed', ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        ProjectUserRoleChoice.objects.all().delete()
        for choice in ['User', 'Manager', 'Group', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for name, attribute_type, has_usage, is_private in (
            ('Project ID', 'Text', False, False),
            ('Account Number', 'Int', False, True),
            ('Auto Disable User Notifications', 'Yes/No', False, True),
        ):
            ProjectAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)

        ProjectTypeChoice.objects.all().delete()
        for choice in ['Research', 'Class', ]:
            ProjectTypeChoice.objects.get_or_create(name=choice)
