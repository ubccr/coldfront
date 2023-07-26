from django.core.management.base import BaseCommand
from coldfront.config.defaults import PROJECT_DEFAULTS as defaults
from coldfront.core.project.models import (
    AttributeType,
    ProjectStatusChoice,
    ProjectAttributeType,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectReviewStatusChoice,
)


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        for choice in defaults['statuschoices']:
            ProjectStatusChoice.objects.get_or_create(name=choice)

        for choice in defaults['projectreviewstatuschoices']:
            ProjectReviewStatusChoice.objects.get_or_create(name=choice)

        for choice in defaults['projectuserrolechoices']:
            ProjectUserRoleChoice.objects.get_or_create(name=choice)

        for choice in defaults['projectuserstatuschoices']:
            ProjectUserStatusChoice.objects.get_or_create(name=choice)

        for attribute_type in defaults['attrtypes']:
            AttributeType.objects.get_or_create(name=attribute_type)

        for name, attribute_type, has_usage, is_private in defaults['projectattrtypes']:
            ProjectAttributeType.objects.get_or_create(
                name=name,
                attribute_type=AttributeType.objects.get(name=attribute_type),
                has_usage=has_usage,
                is_private=is_private,
            )
