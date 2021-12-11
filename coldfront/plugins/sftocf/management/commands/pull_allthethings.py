# Look at storagereport - pulls from AllTheThings
#
# poshbot.RCTools:StorageReport
#
# https://gitlab-int.rc.fas.harvard.edu/common/poshbot.rctools/-/blob/master/PoshBot.RCTools/Public/allthethings.ps1

import json
import requests

from coldfront.core.utils.common import import_from_settings
import logging


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):

        neo4jp = import_from_settings('neo4jp')

        url = "https://allthethings.rc.fas.harvard.edu:7473/db/data/transaction/commit"

        data = '{"statements": [{"statement": "MATCH p=(g:Group)-[:Owns]-(e:Volume) RETURN datetime(e.DotsLVSUpdateDate) as update_date,  datetime(e.DotsLVDisplayUpdateDate) as display_date, null as end_date, g.ADSamAccountName as lab, e.LogicalVolume as fs_path, e.Hostname as server, \"Volume\" as storage_type, \"\" as backup, (e.SizeGB) as gb_allocation, (e.UsedGB) as gb_usage, e.filequota as files_quota,e.files as files,\"\" as status,\"\" as hw_model_id, \"\" as service_tier, \"\" as security_level, \"\" as note"}]}'
        headers = { 'accept': 'application/json,charset=UTF-8', 'authorization': neo4jp, 'content-type': 'application/json', }

        resp = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

        with open('allthethings_output.json', 'w') as f:
            f.write(resp.text)
