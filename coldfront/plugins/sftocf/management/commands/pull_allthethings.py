import os
import re
import json
import logging
import requests

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import Allocation, AllocationAttribute

logger = logging.getLogger(__name__)

with open("coldfront/plugins/sftocf/servers.json", "r") as myfile:
    svp = json.loads(myfile.read())

vol_search = "|".join([i for l in [v.keys() for s, v in svp.items()]for i in l])

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):

        neo4jp = os.environ['neo4jp']
        print(neo4jp)

        url = "https://allthethings.rc.fas.harvard.edu:7473/db/data/transaction/commit"

        query = {"statements": [{"statement": f"MATCH (g:Group)--(n)\
            WHERE (n:IsilonPath OR n:Quota) AND \
            ((n.filesystem =~ '.*{vol_search}.*') OR (n.Isilon =~ '.*{vol_search}.*'))\
            RETURN datetime(n.DotsLFSUpdateDate) as update_date,\
            g.ADSamAccountName as lab,\
            n.filesystem as lfs_volume, \
            n.limitGB as lfs_limitgb,\
            n.quotaGB as lfs_quotagb,\
            n.Isilon as isi_volume,\
            n.hasQuota as isi_hasquota,\
            n.softGB as isi_softgb,\
            n.hardGB as isi_hardgb"
            }]
        }
        headers = { 'accept': 'application/json',
                    'authorization': neo4jp,
                    'content-type': 'application/json', }

        resp = requests.post(url, headers=headers, data=json.dumps(query), verify=False)

        resp_json = json.loads(resp.text)
        cols = resp_json['results'][0]['columns']
        data = resp_json['results'][0]['data']
        resp_json_formatted = [dict(zip(cols,rowdict['row'])) for rowdict in data]

        with open('coldfront/plugins/sftocf/data/allthethings_output.json', 'w') as f:
            f.write(json.dumps(resp_json_formatted, indent=2))
