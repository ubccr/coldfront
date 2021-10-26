from coldfront.plugins.sftocf.pipeline import *
from django.core.management.base import BaseCommand, CommandError
import logging


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        usage_stats = pull_sf()
        for statdict in usage_stats:
            try:
                coldfrontdb.update_usage(statdict)
            except Exception as e:
                logger.debug("EXCEPTION FOR ENTRY: {}".format(e))
