from django.core.management.base import BaseCommand

from coldfront.core.project.models import ProjectAdminActionChoice


class Command(BaseCommand):
    help = 'add default project related choices'

    def handle(self, *args, **options):
        for admin_action_choice in (
            'Approved project request',
            'Denied project request',
            'Approved project review',
            'Denied project review'
        ):
            ProjectAdminActionChoice.objects.get_or_create(
                name=admin_action_choice
            )
