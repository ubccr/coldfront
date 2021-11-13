from coldfront.plugins.sftocf.pipeline import ColdFrontDB
from django.core.management.base import BaseCommand, CommandError
import logging


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--volume',
            dest='volume',
            default=None,
            help='name of volume',
        )

    def handle(self, *args, **kwargs):
        volume = volume = kwargs['volume']
        cfdb = ColdFrontDB()
        filepaths = cfdb.pull_sf(volume=volume)
        cfdb.push_cf(filepaths)
