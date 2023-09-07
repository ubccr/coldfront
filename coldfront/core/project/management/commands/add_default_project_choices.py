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
        for choice in ['New', 'Active', 'Archived', ]:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        for choice in ['Completed', 'Pending', ]:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        for choice in ['User', 'Manager', ]:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        for choice in ['Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed', ]:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for name, attribute_type, has_usage, is_private in (
            # UBCCR defaults
            ('Project ID', 'Text', False, False),
            ('Account Number', 'Int', False, True),
        ):
            ProjectAttributeType.objects.update_or_create(
                name=name,
                defaults={
                    'attribute_type': AttributeType.objects.get(name=attribute_type),
                    'has_usage': has_usage,
                    'is_private': is_private
                }
            )
