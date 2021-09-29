from coldfront.plugins.sftocf.pipeline import *
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

        server = StarFishServer(servername)


        datestr = datetime.today().strftime("%Y%m%d")
        filepath = f"sf_query_{servername}_{datestr}.json"

        if Path(filepath).exists():
            pass
        else:
            filecontents = collect_starfish_json(server, servername, volume, volumepath)
            with open(filepath, "w") as fp:
                json.dump(filecontents, fp, sort_keys=True, indent=4)


        coldfrontdb = ColdFrontDB()
        with open(filepath, "r") as myfile:
            data = myfile.read()
        usage_stats = json.loads(data)
        usage_stats["contents"] = [i for l in usage_stats["contents"] for i in l]
        for statdict in usage_stats["contents"]:
            if (
                statdict["groupname"] != "bicepdata_group"
                and statdict["username"] != "root"
            ):
                logger.debug(statdict)
                try:
                    coldfrontdb.update_usage(statdict)
                except Exception as e:
                    logger.debug("EXCEPTION FOR LAST ENTRY: {}".format(e))
