import os
import re
import json
import time
import timeit
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta

from django.utils import timezone
from ifxuser.models import IfxUser, Organization
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta
from ifxbilling.models import Account, BillingRecord, ProductUsage

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import Project, ProjectUser#, DoesNotExist
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeUsage

datestr = datetime.today().strftime("%Y%m%d")
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'coldfront/plugins/fasrc/data/logs/{datestr}.log', 'w')
logger.addHandler(filehandler)


with open("coldfront/plugins/fasrc/servers.json", "r") as myfile:
    svp = json.loads(myfile.read())

def record_process(func):
    """Wrapper function for logging"""
    def call(*args, **kwargs):
        funcdata = "{} {}".format(func.__name__, func.__code__.co_firstlineno)
        logger.debug("\n{} START.".format(funcdata))
        result = func(*args, **kwargs)
        logger.debug("{} END. output:\n{}\n".format(funcdata, result))
        return result
    return call

class AllTheThingsConn:

    def __init__(self):
        self.url = "https://allthethings.rc.fas.harvard.edu:7473/db/data/transaction/commit"
        self.token = import_from_settings('NEO4JP')
        self.headers = generate_headers(self.token)

    def pull_quota_data(self):
        result_file = 'coldfront/plugins/fasrc/data/allthethings_output.json'
        vol_search = "|".join([i for l in [v.keys() for s, v in svp.items()]for i in l])
        logger.debug(f"vol_search: {vol_search}")


        quota = {"match": "[:HasQuota]-(e:Quota)",
            "where":f"WHERE (e.filesystem =~ '.*({vol_search}).*')",
            "storage_type":"\"Quota\"",
            "usedgb": "usedGB",
            "fs_path":"filesystem",
            "server":"filesystem",
            "unique":"datetime(e.DotsLFSUpdateDate) as begin_date"}

        isilon = {"match": "[:Owns]-(e:IsilonPath)",
            "where":f"WHERE (e.Isilon =~ '.*({vol_search}).*')",
            "storage_type":"\"Isilon\"",
            "fs_path":"Path",
            "server":"Isilon",
            "usedgb": "UsedGB",
            "unique":"datetime(e.DotsUpdateDate) as begin_date"}

        # volume = {"match": "[:Owns]-(e:Volume)",
        #     "where": "",
        #     "storage_type":"\"Volume\"",
        #     "fs_path":"LogicalVolume",
        #     "server":"Hostname",
        #     "unique":"datetime(e.DotsLVSUpdateDate) as update_date, \
        #             datetime(e.DotsLVDisplayUpdateDate) as display_date"}

        queries = {"statements": []}

        for d in [quota, isilon]:
            statement = {"statement": f"MATCH p=(g:Group)-{d['match']} \
                    {d['where']} RETURN\
                    {d['unique']}, \
                    g.ADSamAccountName as lab,\
                    (e.SizeGB / 1024) as tb_allocation, \
                    (e.{d['usedgb']} / 1024) as tb_usage,\
                    e.{d['fs_path']} as fs_path,\
                    {d['storage_type']} as storage_type, \
                    e.{d['server']} as server"}
            queries['statements'].append(statement)

        resp = requests.post(self.url, headers=self.headers, data=json.dumps(queries), verify=False)
        resp_json = json.loads(resp.text)
        # logger.debug(resp_json)
        result_dicts = [i for i in resp_json['results']]
        resp_json_formatted = [dict(zip(rdict['columns'],entrydict['row'])) \
                for rdict in result_dicts for entrydict in rdict['data'] ]
        resp_json_by_lab = {entry['lab']:[] for entry in resp_json_formatted}
        for entry in resp_json_formatted:
            if (entry['storage_type'] == 'Quota' and entry['tb_usage'] in [0, None]) or\
            (entry['storage_type'] == 'Isilon' and entry['tb_allocation'] in [0, None]):
                logger.debug(f"removed: {entry}")
                continue
            resp_json_by_lab[entry['lab']].append(entry)
        # logger.debug(resp_json_by_lab)
        resp_json_by_lab_cleaned = {k:v for k, v in resp_json_by_lab.items() if v}
        with open(result_file, 'w') as f:
            f.write(json.dumps(resp_json_by_lab_cleaned, indent=2))
        return result_file

    def push_quota_data(self, result_file):
        result_json = read_json(result_file)
        for lab, allocations in result_json.items():
            logger.debug(f"project: {lab}")
            # Find the correct allocation_allocationattributes to update by:
            # 1. finding the project with a name that matches lab.lab
            try:
                proj_query = Project.objects.get(title=lab)
            except Project.DoesNotExist:
                logger.info(f"ERROR: cannot find matching project")
                continue
            for allocation in allocations:
                # 2. find the resource that matches/approximates the server value
                r_str = allocation['server'].replace("01.rc.fas.harvard.edu", "")\
                            .replace("/n/", "")
                try:
                    resource = Resource.objects.get(name__contains=r_str)
                except Resource.DoesNotExist:
                    logger.info(f"ERROR: cannot find matching resource")
                    continue
                # logger.info(f"resource: {resource.__dict__}")


                # 3. find the allocation with a matching project and resource_type
                try:
                    a = Allocation.objects.get(  project=proj_query,
                                                resources__id=resource.id,
                                                status__name='Active'   )
                except Allocation.DoesNotExist:
                    logger.info("ERROR: cannot find matching allocation")
                    continue
                except Allocation.MultipleObjectsReturned:
                    logger.info("WARNING: two allocations returned. If l3 in group name, will"
                        "choose the FASSE option; if not, will choose otherwise.")
                    just_str = "FASSE" if "_l3" in lab else "InformationFor"
                    a = Allocation.objects.get( project=proj_query,
                                                justification__contains=just_str,
                                                resources__id=resource.id,
                                                status__name='Active'   )


                logger.info(f"allocation: {a.__dict__}")

                # 4. get the allocation_attribute that has allocation_attribute_type=1 (storagequota)
                #    and allocation=a.id.
                a_quota = AllocationAttribute.objects.get(  allocation=a.id,
                                                            allocation_attribute_type=1)
                a_usage = AllocationAttributeUsage.objects.get( allocation_attribute=a_quota.id)



def generate_headers(token):
    """Generate "headers" attribute by using the "token" attribute.
    """
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer {}".format(token),
    }
    return headers

def read_json(filepath):
    logger.debug("read_json for {}".format(filepath))
    with open(filepath, "r") as myfile:
        data = json.loads(myfile.read())
    return data
