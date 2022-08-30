import logging

from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.fasrc.utils import AllTheThingsConn
from coldfront.core.allocation.models import Allocation, AllocationAttribute

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect group-level quota and usage data from ATT and insert it into the
    Coldfront database.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--volumes',
            dest='volumes',
            default=None,
            help='volumes to collect, with commas separating the names',
        )

    def handle(self, *args, **kwargs):
        volumes = volumes = kwargs['volumes']
        if volumes:
            volumes = volumes.split(",")
        attconn = AllTheThingsConn()
        result_file = attconn.pull_quota_data(volumes=volumes)
        attconn.push_quota_data(result_file)
