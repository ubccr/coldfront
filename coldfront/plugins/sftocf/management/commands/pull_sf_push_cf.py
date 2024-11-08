
import logging

from django.core.management.base import BaseCommand

from coldfront.plugins.sftocf.pipeline import RESTDataPipeline, RedashDataPipeline

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Collect usage data from Starfish and insert it into the Coldfront database.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--volume',
            dest='volume',
            default=None,
            help='name of volume, if update is to be confined to just one',
        )
        parser.add_argument(
            '--pulltype',
            dest='pulltype',
            default='redash',
            help='use either "redash" or "rest" pipeline',
        )

    def handle(self, *args, **kwargs):
        volume = volume = kwargs['volume']
        pulltype = pulltype = kwargs['pulltype']
        if pulltype == 'redash':
            data_pull = RedashDataPipeline(volume)
        elif pulltype == 'rest':
            data_pull = RESTDataPipeline(volume)
        else:
            raise ValueError('unrecognized type argument')

        allocationquerymatch_objs, user_models = data_pull.clean_collected_data()
        data_pull.update_coldfront_objects(user_models)

        logger.debug('pull_sf_push_cf complete')
