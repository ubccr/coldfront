import json
import logging

import pandas as pd
import requests

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import (
    log_missing,
    read_json,
    save_json,
    id_present_missing_projects
)
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import AllocationAttributeType


logger = logging.getLogger(__name__)

ATT_VERIFY = import_from_settings('ATT_VERIFY')

class ATTAllocationQuery:

    def __init__(self):
        self.queries = {'statements': []}

    def produce_query_statement(self, vol_type, volumes=None):

        query_dict = {
            'quota': {
                'volumes': '|'.join(r.name.split('/')[0] for r in Resource.objects.filter(parent_resource__name='Tier 0')),
                'relation': 'HasQuota',
                'match': "(e:Quota) MATCH (d:ConfigValue {Name: 'Quota.Invocation'})",
                'server': 'filesystem',
                'validation_query':
                    "NOT ((e.SizeGB IS null) OR (e.usedBytes = 0 AND e.SizeGB = 1024))\
                    AND (datetime() - duration('P31D') <= datetime(r.DotsLFSUpdateDate))\
                    AND NOT (e.Path IS null)",
                'r_updated': 'DotsLFSUpdateDate',
                'storage_type': 'Quota',
                'usedgb': 'usedGB',
                'sizebytes': 'limitBytes',
                'usedbytes': 'usedBytes',
                'fs_path': 'Path',
                'server_replace': '/n/',
                'path_def': "substring(e.Path, size('/n/') + size(split(e.Path, '/')[2]) + 1)",
                'unique':'datetime(e.DotsLFSUpdateDate) as begin_date'
            },
            'isilon': {
                'volumes': '|'.join(r.name.split('/')[0] for r in Resource.objects.filter(parent_resource__name='Tier 1')),
                'relation': 'Owns',
                'match': "(e:IsilonPath) MATCH (d:ConfigValue {Name: 'IsilonPath.Invocation'})",
                'server': 'Isilon',
                'validation_query': "r.DotsUpdateDate = d.DotsUpdateDate\
                    AND NOT (e.Path =~ '.*/rc_admin/.*')\
                    AND (e.Path =~ '.*labs.*')\
                    AND (datetime() - duration('P31D') <= datetime(r.DotsUpdateDate))\
                    AND NOT (e.SizeGB = 0)",
                'fs_path':'Path',
                'r_updated': 'DotsUpdateDate',
                'storage_type': 'Isilon',
                'usedgb': 'UsedGB',
                'sizebytes': 'SizeBytes',
                'usedbytes': 'UsedBytes',
                'server_replace': '01.rc.fas.harvard.edu',
                'path_def': "replace(e.Path, '/ifs/', '')",
                'unique': 'datetime(e.DotsUpdateDate) as begin_date'
            },
            'volume': {
                'volumes': '|'.join(r.name.split('/')[0] for r in Resource.objects.filter(parent_resource__name='Tier 2')),
                'relation': 'Owns',
                'match': '(e:Volume)',
                'server': 'Hostname',
                'validation_query': 'NOT (e.SizeGB = 0)',
                'r_updated': 'DotsLVSUpdateDate',
                'storage_type': 'Volume',
                'fs_path': 'LogicalVolume',
                'path_def': "replace(e.LogicalVolume, '/dev/data/', '')",
                'usedgb': 'UsedGB',
                'sizebytes': 'SizeGB * 1000000000',
                'usedbytes': 'UsedGB * 1000000000',
                'server_replace': '.rc.fas.harvard.edu',
                'unique': 'datetime(e.DotsLVSUpdateDate) as update_date,\
                        datetime(e.DotsLVDisplayUpdateDate) as display_date'
            },
        }
        d = query_dict[vol_type]

        statement = {
            'statement': f"MATCH p=(g:Group)-[r:{d['relation']}]-{d['match']}\
            WHERE g.ATTStaleData = false AND (e.{d['server']} =~ '.*({d['volumes']}).*')\
            AND {d['validation_query']}\
            AND NOT (g.ADSamAccountName =~ '.*(disabled|rc_admin).*')\
            RETURN\
            {d['unique']},\
            g.ADSamAccountName as lab,\
            (e.SizeGB / 1024.0) as tb_allocation,\
            e.{d['sizebytes']} as byte_allocation,\
            e.{d['usedbytes']} as byte_usage,\
            (e.{d['usedgb']} / 1024.0) as tb_usage,\
            {d['path_def']} as fs_path,\
            '{d['storage_type']}' as storage_type,\
            datetime(r.{d['r_updated']}) as rel_updated,\
            replace(e.{d['server']}, '{d['server_replace']}', '') as server"
        }
        self.queries['statements'].append(statement)


class QuotaDataPuller:
    """pull and standardize quota data"""

    def __init__(self, volumes=None):
        self.volumes = volumes

    def pull(self, standard):
        standardizer = self.get_standardizer(standard)
        return standardizer()

    def get_standardizer(self, standard):
        if standard == 'ATTQuery':
            return self._standardize_attquery
        if standard == 'NESEfile':
            return self._standardize_nesefile
        raise ValueError(standard)

    def _standardize_attquery(self):
        attconn = AllTheThingsConn(volumes=self.volumes)
        resp_json = attconn.pull_quota_data()
        return attconn.format_query_results(resp_json)

    def _standardize_nesefile(self):
        datafile = 'nese_data/pools'
        header_file = 'nese_data/pools.header'
        with open('nese_data/local_groupkey') as groupkey_file:
            translator = dict((
                kv.split('=') for kv in (l.strip('\n') for l in groupkey_file)
            ))
        headers_df = pd.read_csv(header_file, header=0, sep='\s+')
        headers = headers_df.columns.values.tolist()
        data = pd.read_csv(datafile, names=headers, sep='\s+')
        data = data.loc[data['pool'].str.contains('1')]
        data['fs_path'] = data['pool']
        data['lab'] = data['pool'].str.replace('1', '').str.replace('hugl', '').str.replace('hus3', '')
        data['server'] = 'nesetape'
        data['storage_type'] = 'tape'
        data['byte_allocation'] = data['mib_capacity'] * 1048576
        data['byte_usage'] = data['mib_used'] * 1048576
        data['tb_allocation'] = round(((data['mib_capacity']+ data['mib_capacity']*0.025) / 953674.3164), -1)
        data['tb_usage'] = data['mib_used'] / 953674.3164
        data = data[[
            'lab', 'server', 'storage_type', 'byte_allocation',
            'byte_usage', 'tb_allocation', 'tb_usage', 'fs_path',
        ]]
        nesedict = data.to_dict(orient='records')
        for d in nesedict:
            if translator.get(d['lab']):
                d['lab'] = translator[d['lab']]
            else:
                d['lab'] = d['lab']+'_lab'
        return nesedict


class AllTheThingsConn:

    def __init__(self, volumes=None):
        self.url = 'https://allthethings01.rc.fas.harvard.edu:7473/db/neo4j/tx/commit'
        self.token = import_from_settings('NEO4JP', '')
        self.headers = generate_headers(self.token)
        self.volumes = volumes

    def post_query(self, query):
        resp = requests.post(self.url, headers=self.headers, data=json.dumps(query), verify=ATT_VERIFY)
        return json.loads(resp.text)

    def format_query_results(self, resp_json):
        result_dicts = list(resp_json['results'])
        return [dict(zip(d['columns'], ed['row'])) for d in result_dicts for ed in d['data']]

    def stage_user_member_query(self, groupsearch, pi=False):
        match_vars = '(u:User)-[r:MemberOf|ManagedBy]-(g:Group) WHERE'
        return_vars = 'type(r) AS relationship, g.ADManaged_By AS group_manager'
        if pi:
            match_vars = '(g:Group) WITH g MATCH (u:User)\
                    WHERE u.ADSamAccountName = g.ADManaged_By AND'
            return_vars = 'u.ADParentCanonicalName AS path, u.ADDepartment AS department'
        query = {'statements': [{
            'statement': f"MATCH {match_vars} (g.ADSamAccountName =~ '({groupsearch})')\
                RETURN\
                u.ADgivenName AS first_name,\
                u.ADsurname AS last_name,\
                u.ADSamAccountName AS user_name,\
                u.ADenabled AS user_enabled,\
                g.ADSamAccountName AS group_name,\
                {return_vars},\
                g.ADManaged_By AS group_manager,\
                u.ADgidNumber AS user_gid_number,\
                u.ADTitle AS title,\
                u.ADCompany AS company,\
                g.ADgidNumber AS group_gid_number"
        }]}
        resp_json = self.post_query(query)
        resp_json_formatted = self.format_query_results(resp_json)
        return resp_json_formatted

    def collect_group_membership(self, groupsearch):
        """
        Collect user, and relationship information for a lab or labs from ATT.
        """
        resp_json_formatted = self.stage_user_member_query(groupsearch)
        return resp_json_formatted

    def collect_pi_data(self, grouplist):
        """collect information on pis for a given list of groups
        """
        resp_json_formatted = self.stage_user_member_query(grouplist, pi=True)
        return resp_json_formatted

    def pull_quota_data(self):
        """Produce JSON file of quota data for LFS and Isilon from AlltheThings.
        Parameters
        ----------
        volumes : List of volume names to collect. Optional, default None.
        """
        logger = logging.getLogger('coldfront.import_quotas')
        query = ATTAllocationQuery()
        query.produce_query_statement('isilon', volumes=self.volumes)
        query.produce_query_statement('quota', volumes=self.volumes)
        query.produce_query_statement('volume', volumes=self.volumes)
        resp_json = self.post_query(query.queries)
        logger.debug(resp_json)
        return resp_json


def matched_dict_processing(allocation, data_dicts, paired_allocs, log_message):
    logger = logging.getLogger('coldfront.import_quotas')
    if len(data_dicts) == 1:
        logger.debug(log_message)
        paired_allocs[allocation] = data_dicts[0]
    else:
        logger.warning('too many matches for allocation %s %s: %s',
            allocation.pk, allocation, data_dicts)
    return paired_allocs


def pair_allocations_data(project, quota_dicts):
    """pair allocations with usage dicts"""
    logger = logging.getLogger('coldfront.import_quotas')
    allocs = project.allocation_set.filter(
        status__name__in=['Active','Pending Deactivation'],
        resources__resource_type__name='Storage'
    )
    paired_allocs = {}
    # first, pair allocations with those that have same
    for allocation in allocs:
        dicts = [
            d for d in quota_dicts
            if d['fs_path'] and d['fs_path'].lower() == allocation.path.replace('HDD/', '').replace('SSD-HGST/', '').replace('SSD/', '').lower()
            and d['server'] in allocation.resources.first().name
        ]
        if dicts:
            log_message = f'Path-based match: {allocation}, {allocation.path}, {dicts[0]}'
            paired_allocs = matched_dict_processing(allocation, dicts, paired_allocs, log_message)
    unpaired_allocs = [(a.pk, a, a.path) for a in allocs if a not in paired_allocs]
    unpaired_dicts = [d for d in quota_dicts if d not in paired_allocs.values()]
    if unpaired_dicts or unpaired_allocs:
        print(
            f"unpaired allocation data. Allocation: {unpaired_allocs} | Dict: {unpaired_dicts}"
        )
        logger.warning(
            "unpaired allocation data. Allocation: %s | Dict: %s", unpaired_allocs, unpaired_dicts
        )
    return paired_allocs


def push_quota_data(result_file):
    """update group quota & usage values in Coldfront from a JSON of quota data.
    """
    logger = logging.getLogger('coldfront.import_quotas')
    errored_allocations = {}
    missing_allocations = []
    result_json = read_json(result_file)
    counts = {'proj_err': 0, 'res_err':0, 'all_err':0, 'complete':0}
    # produce lists of present labs & labs w/o projects
    result_json_cleaned, proj_models = match_entries_with_projects(result_json)
    counts['proj_err'] = len(result_json) - len(result_json_cleaned)

    # collect commonly used database objects here
    proj_models = proj_models.prefetch_related('allocation_set')
    allocation_attribute_types = AllocationAttributeType.objects.all()

    for lab, quota_dicts in result_json_cleaned.items():
        logger.info('PROJECT: %s ====================================', lab)
        # Find the correct allocation_allocationattributes to update by:
        # 1. finding the project with a name that matches lab.lab
        project = proj_models.get(title=lab)
        # 2. pair project allocations with data
        allocation_data_dict = pair_allocations_data(project, quota_dicts)
        for allocation, data_dict in allocation_data_dict.items():
            try:
                # 3. get the storage quota TB allocation_attribute that has allocation=a.
                allocation_values = {
                    'Storage Quota (TB)': [data_dict['tb_allocation'],data_dict['tb_usage']]
                }
                if data_dict['byte_allocation'] is not None:
                    allocation_values['Quota_In_Bytes'] = [
                        data_dict['byte_allocation'], data_dict['byte_usage']
                    ]
                else:
                    logger.warning(
                        'no byte_allocation value for allocation %s, lab %s on resource %s',
                        allocation.pk, lab, data_dict['server']
                    )
                for k, v in allocation_values.items():
                    allocation_attr_type_obj = allocation_attribute_types.get(name=k)
                    alloc_attr_obj, _ = allocation.allocationattribute_set.update_or_create(
                        allocation_attribute_type=allocation_attr_type_obj,
                        defaults={'value': v[0]}
                    )
                    alloc_attr_obj.allocationattributeusage.value = v[1]
                    alloc_attr_obj.allocationattributeusage.save()

                counts['complete'] += 1
            except Exception as exc:
                allocation_name = f"{data_dict['lab']}/{data_dict['server']}"
                errored_allocations[allocation_name] = exc
    log_missing('allocation', missing_allocations)
    logger.warning('error counts: %s', counts)
    if errored_allocations:
        logger.warning('errored_allocations:\n%s', errored_allocations)


def match_entries_with_projects(result_json):
    """Remove and report allocations for projects not in Coldfront"""
    # produce lists of present labs & labs w/o projects
    lablist = list(set(k for k in result_json))
    proj_models, missing_projs = id_present_missing_projects(lablist)

    log_missing('project', missing_projs)
    if missing_projs:
        logger.warning('missing projects: %s', missing_projs)
    # remove them from result_json
    missing_proj_titles = [list(p.values())[0] for p in missing_projs]
    [result_json.pop(t) for t in missing_proj_titles]
    return result_json, proj_models


def pull_push_quota_data(volumes=None):
    logger = logging.getLogger('coldfront.import_quotas')
    att_data = QuotaDataPuller(volumes=volumes).pull('ATTQuery')
    nese_data = QuotaDataPuller(volumes=volumes).pull('NESEfile')
    combined_data = att_data + nese_data
    resp_json_by_lab = {entry['lab']:[] for entry in combined_data}
    [resp_json_by_lab[e['lab']].append(e) for e in combined_data]
    logger.debug(resp_json_by_lab)
    result_file = 'local_data/att_nese_quota_data.json'
    save_json(result_file, resp_json_by_lab)
    push_quota_data(result_file)


def generate_headers(token):
    """Generate 'headers' attribute by using the 'token' attribute.
    """
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    return headers
