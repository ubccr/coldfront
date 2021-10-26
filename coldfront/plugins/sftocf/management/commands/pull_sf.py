from coldfront.plugins.sftocf.pipeline import pull_sf
from django.core.management.base import BaseCommand, CommandError
import logging


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        pull_sf()
