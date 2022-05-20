from inspect import Attribute
import os

from django.core.management.base import BaseCommand

from coldfront.core.project.models import (ProjectAttributeType,
                                            ProjectReviewStatusChoice,
                                            ProjectStatusChoice,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            AttributeType)

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
        for choice in ['User', 'Manager', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        ProjectUserStatusChoice.objects.all().delete()
        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)
        
        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        ProjectAttributeType.objects.all().delete()
        for name, attribute_type, has_usage, is_private in (
            ('Sample Attr 1', 'Text', False, False),
            ('Sample Attr 2', 'Yes/No', False, True),
            ('Sample Attr 3', 'Int', True, False),
            ('Sample Attr 4', 'Float', True, False),
        ):
            ProjectAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)
        