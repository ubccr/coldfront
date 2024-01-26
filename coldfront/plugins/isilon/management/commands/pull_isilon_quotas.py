from django.core.management.base import BaseCommand

from coldfront.plugins.isilon.utils import update_quotas_usages

class Command(BaseCommand):
    """
    Pull Isilon quotas
    """
    help = 'Pull Isilon quotas'

    def handle(self, *args, **kwargs):
        update_quotas_usages()
