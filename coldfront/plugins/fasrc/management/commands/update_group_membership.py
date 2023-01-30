from django.core.management.base import BaseCommand

from coldfront.plugins.fasrc.utils import update_group_membership

class Command(BaseCommand):
    '''
    Collect group-level quota and usage data from ATT and insert it into the
    Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        update_group_membership()
