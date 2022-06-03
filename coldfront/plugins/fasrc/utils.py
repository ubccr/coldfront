import os
import re
import json
import time
import timeit
import logging
import requests
from pathlib import Path
from functools import reduce
from datetime import datetime, timedelta

import operator
from django.db.models import Q
from django.utils import timezone
from ifxuser.models import IfxUser, Organization
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta
from ifxbilling.models import Account, BillingRecord, ProductUsage

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import Project, ProjectUser#, DoesNotExist
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import   (Allocation,
                                                AllocationAttribute,
                                                AllocationAttributeType,
                                                AllocationAttributeUsage)

datestr = datetime.today().strftime("%Y%m%d")
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'coldfront/plugins/fasrc/data/logs/{datestr}.log', 'w')
logger.addHandler(filehandler)


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
        """Produce JSON file of quota data for LFS and Isilon from AlltheThings.
        """
        result_file = 'coldfront/plugins/fasrc/data/allthethings_output.json'
        svp = read_json("coldfront/plugins/fasrc/servers.json")
        volumes = "|".join([i for l in [v.keys() for s, v in svp.items()]for i in l])
        logger.debug(f"volumes: {volumes}")

        quota = {"match": "[:HasQuota]-(e:Quota)",
            "where":f"WHERE (e.filesystem =~ '.*({volumes}).*')",
            "storage_type":"\"Quota\"",
            "usedgb": "usedGB",
            "sizebytes": "limitBytes",
            "usedbytes": "usedBytes",
            "fs_path":"filesystem",
            "server":"filesystem",
            "unique":"datetime(e.DotsLFSUpdateDate) as begin_date"}

        isilon = {"match": "[:Owns]-(e:IsilonPath)",
            "where":f"WHERE (e.Isilon =~ '.*({volumes}).*')",
            "storage_type":"\"Isilon\"",
            "fs_path":"Path",
            "server":"Isilon",
            "usedgb": "UsedGB",
            "sizebytes": "SizeBytes",
            "usedbytes": "UsedBytes",
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
                    e.{d['sizebytes']} as byte_allocation,\
                    e.{d['usedbytes']} as byte_usage,\
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
        """Use JSON of collected ATT data to update group quota & usage values in Coldfront.
        """
        result_json = read_json(result_file)
        counts = {"proj_err": 0, "res_err":0, "all_err":0, "complete":0}
        # produce list of present labs
        lablist = [k for k in result_json.keys()]
        proj_models = Project.objects.filter(title__in=lablist)
        proj_titles = [p.title for p in proj_models]
        # log labs w/o projects, remove them from result_json
        missing_projs = log_missing("project", proj_titles,lablist)
        counts['proj_err'] = len(missing_projs)
        [result_json.pop(key) for key in missing_projs]

        # clean result_json - edit "server" value
        for l in result_json.values():
            for a in l:
                a['server'] = a['server'].replace("01.rc.fas.harvard.edu", "")\
                        .replace("/n/", "")

        # produce set of server values for which to locate matching resources
        resource_set = set([a['server'] for l in result_json.values() for a in l])
        # get resource models
        res_models = Resource.objects.filter(reduce(operator.or_, (Q(name__contains=x) for x in resource_set)))
        res_names = [str(r.name).split("/")[0] for r in res_models]
        missing_res = log_missing("resource", res_names, resource_set)
        counts['proj_err'] = len(missing_res)

        for k, v in result_json.items():
            result_json[k] = [a for a in v if a['server'] not in missing_res]

        for lab, allocations in result_json.items():
            logger.debug(f"PROJECT: {lab} ====================================")
            # Find the correct allocation_allocationattributes to update by:
            # 1. finding the project with a name that matches lab.lab
            proj_query = proj_models.get(title=lab)
            for allocation in allocations:
                lab_allocation = allocation['tb_allocation']
                lab_usage = allocation['tb_usage']
                # 2. find the resource that matches/approximates the server value
                r_str = allocation['server'].replace("01.rc.fas.harvard.edu", "")\
                            .replace("/n/", "")
                resource = res_models.get(name__contains=r_str)
                # logger.info(f"resource: {resource.__dict__}")


                # 3. find the allocation with a matching project and resource_type
                a = Allocation.objects.filter(  project=proj_query,
                                                resources__id=resource.id,
                                                status__name='Active'   )
                if a.count() == 1:
                    a = a.first()
                elif a.count() < 1:
                    res_str = allocation['server']
                    log_missing("allocation", [], [res_str], group=proj_query.title, pattern="G,I,D")
                    counts['all_err'] += 1
                    continue
                elif a.count() > 1:
                    logger.info("WARNING: multiple allocations returned. If LFS, will "
                        "choose the FASSE option; if not, will choose otherwise.")
                    just_str = "FASSE" if allocation['storage_type'] == "Isilon" else "Information for"
                    a = Allocation.objects.get( project=proj_query,
                                                justification__contains=just_str,
                                                resources__id=resource.id,
                                                status__name='Active'   )


                logger.info(f"allocation: {a.__dict__}")

                # 4. get the storage quota TB allocation_attribute that has allocation=a.
                for alloc_attribute_type in ('Storage Quota (TB)', 'Quota_In_Bytes'):
                    allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                        name=alloc_attribute_type)
                    try:
                        allocation_attribute_obj = AllocationAttribute.objects.get(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=a,
                        )
                        allocation_attribute_obj.value = lab_allocation
                        allocation_attribute_obj.save()
                        allocation_attribute_exist = True
                    except AllocationAttribute.DoesNotExist:
                        allocation_attribute_exist = False

                    if (not allocation_attribute_exist):
                        allocation_attribute_obj,_ =AllocationAttribute.objects.get_or_create(
                            allocation_attribute_type=allocation_attribute_type_obj,
                            allocation=a,
                            value = lab_allocation)
                        allocation_attribute_type_obj.save()

                    allocation_attribute_obj.allocationattributeusage.value = lab_usage
                    allocation_attribute_obj.allocationattributeusage.save()

                # 5. AllocationAttribute
                allocation_attribute_type_payment = AllocationAttributeType.objects.get(name='RequiresPayment')
                allocation_attribute_payment, _ = AllocationAttribute.objects.get_or_create(
                        allocation_attribute_type=allocation_attribute_type_payment,
                        allocation=a,
                        value=True)
                allocation_attribute_payment.save()
                counts['complete'] += 1
        logger.info(f"error counts: {counts}")


def log_missing(modelname,
                model_attr_list,
                search_list,
                group="",
                fpath_pref="./coldfront/plugins/fasrc/data/",
                pattern = "I,D"):
    fpath = f'{fpath_pref}missing_{modelname}s.csv'
    missing = [i for i in search_list if i not in [i for i in model_attr_list]]
    if missing:
        datestr = datetime.today().strftime("%Y%m%d")
        patterns = [pattern.replace("I", i).replace("D", datestr).replace("G", group) for i in missing]
        find_or_add_file_line(fpath, patterns)
    return missing


def find_or_add_file_line(filepath, patterns):
    """Find or add lines matching a string contained in a list to a file.

    Parameters
    ----------
    filepath : string
        path and name of file to check.
    patterns : list
        list of lines to find or append to file.
    """
    with open(filepath, 'a+') as f:
        f.seek(0)
        lines = f.readlines()
        for p in patterns:
            if not any(p == line.rstrip('\r\n') for line in lines):
                f.write(p + '\n')


def generate_headers(token):
    """Generate "headers" attribute by using the "token" attribute.
    """
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer {}".format(token),
    }
    return headers

def read_json(filepath):
    logger.debug(f"read_json for {filepath}")
    with open(filepath, "r") as myfile:
        data = json.loads(myfile.read())
    return data
