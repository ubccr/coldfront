from coldfront.plugins.sftocf.pipeline import pull_sf
from django.core.management.base import BaseCommand, CommandError
import logging


logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--server',
            dest='server',
            default="holysfdb01",
            help="name of server",
        )
        parser.add_argument(
            '--volume',
            dest='volume',
            default="holylfs04",
            help='name of volume',
        )
        parser.add_argument(
            '--volpath',
            dest='volpath',
            default="HDD/C/LABS",
            help='path in volume from which to gather usage data',
        )


    def handle(self, *args, **kwargs):
        servername = server = kwargs['server']
        volume = volume = kwargs['volume']
        volumepath = volpath = kwargs['volpath']
        pull_sf(servername, volume, volumepath)
