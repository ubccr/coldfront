from django.core.management.base import BaseCommand, CommandError
from coldfront.plugins.sftocf.utils import ColdFrontDB
import logging


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        cfdb = ColdFrontDB()
        cfdb.pull_sf()