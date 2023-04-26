import os
import logging

from django.core.management.base import BaseCommand

from coldfront.core.utils.fasrc import read_json
from coldfront.plugins.sftocf.utils import pull_sf, push_cf

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
        parser.add_argument(
            '--clean',
            dest='clean',
            default=False,
            help='if true, remove json after entry',
        )

    def handle(self, *args, **kwargs):
        volume = volume = kwargs['volume']
        clean = clean = kwargs['clean']
        filepaths = pull_sf(volume=volume)
        for f in filepaths:
            content = read_json(f)
            errors = push_cf(content)
            if not errors and clean:
                os.remove(f)
        logger.debug('push_cf complete')
