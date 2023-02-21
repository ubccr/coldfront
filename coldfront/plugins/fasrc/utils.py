import json
import logging
from datetime import datetime

import requests
from django.db.models import Q
from django.contrib.auth import get_user_model

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import (log_missing,
                                        select_one_project_allocation,
                                        save_json,
                                        id_present_missing_users,
                                        id_present_missing_resources,
                                        id_present_missing_projects)
from coldfront.core.project.models import ( Project,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            ProjectUser)
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import   (Allocation,
                                                AllocationUser,
                                                AllocationAttribute,
                                                AllocationAttributeType)

today = datetime.today().strftime('%Y%m%d')

logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'logs/{today}.log', 'w')
logger.addHandler(filehandler)


def record_process(func):
    '''Wrapper function for logging'''
    def call(*args, **kwargs):
        funcdata = '{} {}'.format(func.__name__, func.__code__.co_firstlineno)
        logger.debug('\n%s START.', funcdata)
        result = func(*args, **kwargs)
        logger.debug('%s END. output:\n%s\n', funcdata, result)
        return result
    return call


class AllTheThingsConn:

    def __init__(self):
        self.url = 'https://allthethings.rc.fas.harvard.edu:7473/db/data/transaction/commit'
        self.token = import_from_settings('NEO4JP')
        self.headers = generate_headers(self.token)

    def post_query(self, query):
        resp = requests.post(self.url, headers=self.headers, data=json.dumps(query), verify=False)
        return json.loads(resp.text)

    def format_query_results(self, resp_json):
        result_dicts = list(resp_json['results'])
        return [dict(zip(rdict['columns'],entrydict['row'])) \
                for rdict in result_dicts for entrydict in rdict['data'] ]

    def collect_group_membership(self, groupname):
        '''
        Collect user, and relationship information for a given lab from ATT.
        '''
        query = {'statements': [{
                    'statement': f'MATCH (u:User)-[r:MemberOf|ManagedBy]-(g:Group) \
                    WHERE (g.ADName = \'{groupname}\' OR g.ADSamAccountName = \'{groupname}\') \
                    RETURN \
                    u.ADgivenName AS first_name, \
                    u.ADsurname AS last_name, \
                    u.ADSamAccountName AS user_name, \
                    u.ADenabled AS user_enabled, \
                    g.ADName AS group_name,\
                    type(r) AS relationship,\
                    u.ADgidNumber AS user_gid_number, \
                    g.ADgidNumber AS group_gid_number'
                }]}
        resp_json = self.post_query(query)
        resp_json_formatted = self.format_query_results(resp_json)
        return resp_json_formatted


    def pull_quota_data(self, volumes=None):
        '''Produce JSON file of quota data for LFS and Isilon from AlltheThings.
        Parameters
        ----------
        volumes : List of volume names to collect. Optional, default None.
        '''
        result_file = 'coldfront/plugins/fasrc/data/allthethings_output.json'
        if volumes:
            volumes = '|'.join(volumes)
        else:
            volumes = '|'.join([r.name.split('/')[0] for r in Resource.objects.all()])
        logger.debug("volumes: %s", volumes)

        quota = {'match': '[r:HasQuota]-(e:Quota)',
            'where':f"(e.filesystem =~ \'.*({volumes}).*\')",
            'r_updated': 'DotsLFSUpdateDate',
            'storage_type':'\'Quota\'',
            'usedgb': 'usedGB',
            'sizebytes': 'limitBytes',
            'usedbytes': 'usedBytes',
            'fs_path':'filesystem',
            'server':'filesystem',
            'replace': '/n/',
            'unique':'datetime(e.DotsLFSUpdateDate) as begin_date'}

        isilon = {'match': '[r:Owns]-(e:IsilonPath) MATCH (d:ConfigValue {Name: \'IsilonPath.Invocation\'})',
            'where':f"(e.Isilon =~ '.*({volumes}).*') \
                        AND r.DotsUpdateDate = d.DotsUpdateDate \
                        AND NOT (e.Path =~ '.*/rc_admin/.*')",
            'r_updated': 'DotsUpdateDate',
            'storage_type':'\'Isilon\'',
            'fs_path':'Path',
            'server':'Isilon',
            'usedgb': 'UsedGB',
            'sizebytes': 'SizeBytes',
            'usedbytes': 'UsedBytes',
            'replace': '01.rc.fas.harvard.edu',
            'unique':'datetime(e.DotsUpdateDate) as begin_date'}

        # volume = {'match': '[:Owns]-(e:Volume)',
        #     'where': '',
        #     'storage_type':'\'Volume\'',
        #     'fs_path':'LogicalVolume',
        #     'server':'Hostname',
        #     'unique':'datetime(e.DotsLVSUpdateDate) as update_date, \
        #             datetime(e.DotsLVDisplayUpdateDate) as display_date'}

        queries = {'statements': []}

        for d in [quota, isilon]:
            statement = {'statement': f"MATCH p=(g:Group)-{d['match']} \
                    WHERE {d['where']} \
                    AND (datetime() - duration('P31D') <= datetime(r.{d['r_updated']})) \
                    RETURN \
                    {d['unique']}, \
                    g.ADSamAccountName as lab,\
                    (e.SizeGB / 1024.0) as tb_allocation, \
                    e.{d['sizebytes']} as byte_allocation,\
                    e.{d['usedbytes']} as byte_usage,\
                    (e.{d['usedgb']} / 1024.0) as tb_usage,\
                    e.{d['fs_path']} as fs_path,\
                    {d['storage_type']} as storage_type, \
                    datetime(r.{d['r_updated']}) as rel_updated, \
                    replace(e.{d['server']}, '{d['replace']}', '') as server"}
            queries['statements'].append(statement)
        resp_json = self.post_query(queries)
        # logger.debug(resp_json)
        resp_json_formatted = self.format_query_results(resp_json)
        resp_json_by_lab = {entry['lab']:[] for entry in resp_json_formatted}
        for entry in resp_json_formatted:
            if (entry['storage_type'] == 'Quota' and (
                entry['tb_usage'] == None) or (
                    entry['byte_usage'] == 0 and entry['tb_allocation'] == 1)
            ) or\
            (entry['storage_type'] == 'Isilon' and entry['tb_allocation'] in [0, None]):
                logger.debug('removed: %s', entry)
                continue
            resp_json_by_lab[entry['lab']].append(entry)
        # logger.debug(resp_json_by_lab)
        resp_json_by_lab_cleaned = {k:v for k, v in resp_json_by_lab.items() if v}
        save_json(result_file, resp_json_by_lab_cleaned)
        return result_file


    def push_quota_data(self, result_file):
        '''Use JSON of collected ATT data to update group quota & usage values in Coldfront.
        '''
        errored_allocations = {}
        missing_allocations = []
        result_json = read_json(result_file)
        counts = {'proj_err': 0, 'res_err':0, 'all_err':0, 'complete':0}
        # produce lists of present labs & labs w/o projects
        lablist = list(set(k for k in result_json))
        proj_models, missing_projs = id_present_missing_projects(lablist)
        log_missing('project', missing_projs)
        # remove them from result_json
        counts['proj_err'] = len(missing_projs)
        missing_proj_titles = [list(p.values())[0] for p in missing_projs]
        [result_json.pop(t) for t in missing_proj_titles]

        # produce set of server values for which to locate matching resources
        resource_list = list({a['server'] for l in result_json.values() for a in l})
        logger.debug("coldfront resource_list: %s", resource_list)
        res_models, missing_res = id_present_missing_resources(resource_list)
        counts['proj_err'] = len(missing_res)

        # collect commonly used database objects here
        proj_models = proj_models.prefetch_related('allocation_set')
        allocation_attribute_types = AllocationAttributeType.objects.all()
        allocation_attribute_type_payment = allocation_attribute_types.get(name='RequiresPayment')

        for k, v in result_json.items():
            result_json[k] = [a for a in v if a['server'] not in missing_res]

        for lab, allocations in result_json.items():
            logger.info('PROJECT: %s ====================================', lab)
            # Find the correct allocation_allocationattributes to update by:
            # 1. finding the project with a name that matches lab.lab
            proj_query = proj_models.get(title=lab)
            for allocation in allocations:
                try:
                    # 2. find the resource that matches/approximates the server value
                    r_str = allocation['server'].replace("01.rc.fas.harvard.edu", "")\
                                .replace("/n/", "")
                    resource = res_models.get(name__contains=r_str)

                    # 3. find the allocation with a matching project and resource_type
                    alloc_obj = select_one_project_allocation(proj_query, resource, dirpath=allocation['fs_path'])

                    if alloc_obj is None:
                        logger.warning("ERROR: No Allocation for project %s, resource %s",
                                                    proj_query.title, resource.name)
                        missing_allocations.append({
                                "resource_name":resource.name,
                                "project_title": proj_query.title
                                })
                        counts['all_err'] += 1
                    elif alloc_obj == "MultiAllocationError":
                        logger.warning("ERROR: Unresolved multiple allocations for project %s, resource %s",
                                                    proj_query.title, resource.name)
                        counts['all_err'] += 1

                    logger.info("allocation: %s", alloc_obj.__dict__)

                    # 4. get the storage quota TB allocation_attribute that has allocation=a.
                    allocation_values = { 'Storage Quota (TB)':
                                [allocation['tb_allocation'],allocation['tb_usage']]  }
                    if allocation['byte_allocation'] is not None:
                        allocation_values['Quota_In_Bytes'] = [ allocation['byte_allocation'],
                                                                allocation['byte_usage']]
                    else:
                        logger.warning(
                                "no byte_allocation value for allocation %s, lab %s on resource %s",
                                alloc_obj.pk, lab, r_str)
                    for k, v in allocation_values.items():
                        allocation_attribute_type_obj = allocation_attribute_types.get(name=k)
                        allocattribute_obj, _ = alloc_obj.allocationattribute_set.update_or_create(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                defaults={'value': v[0]}
                            )
                        allocattribute_obj.allocationattributeusage.update(value=v[1])

                    # 5. AllocationAttribute
                    alloc_obj.allocationattribute_set.update_or_create(
                            allocation_attribute_type=allocation_attribute_type_payment,
                            defaults={'value':True})
                    counts['complete'] += 1
                except Exception as e:
                    allocation_name = f"{allocation['lab']}/{allocation['server']}"
                    errored_allocations[allocation_name] = e
        log_missing("allocation", missing_allocations)
        logger.warning("error counts: %s", counts)
        logger.warning('errored_allocations:\n%s', errored_allocations)


def update_group_membership():
    '''
    Use ATT's user, group, and relationship information to keep the ProjectUser
    list up-to-date for existing Coldfront Projects.
    '''
    # change logger filehandler
    logger.removeHandler(filehandler)
    handler = logging.FileHandler(f'logs/att_membership_update-{today}.log', 'w')
    logger.addHandler(handler)
    errors = { "no_members": [], "no_users": [], "no_managers": [] }

    # collect commonly used db objects
    projectuser_role_user = ProjectUserRoleChoice.objects.get(name='User')
    projectuserstatus_active = ProjectUserStatusChoice.objects.get(name='Active')
    projectuserstatus_removed = ProjectUserStatusChoice.objects.get(name='Removed')
    projectuserstatus_pendremove = ProjectUserStatusChoice.objects.get(name='Pending - Remove')
    projectuser_role_manager = ProjectUserRoleChoice.objects.get(name='Manager')

    for project in Project.objects.filter(status__name__in=["Active", "New"]).prefetch_related('projectuser_set'):
        # pull membership data for the given project
        proj_name = project.title
        att_conn = AllTheThingsConn()
        logger.debug('updating group membership for %s', proj_name)
        group_data = att_conn.collect_group_membership(proj_name)
        logger.debug('raw AD group data:\n%s', group_data)
        group_data = [group for group in group_data if group['user_enabled'] is True]
        if not group_data:
            errors['no_members'].append(proj_name)
            continue
        # project = Project.objects.get(title=proj_name)
        projectusernames = [pu.user.username for pu in project.projectuser_set.filter(
                    (~Q(status__name='Removed'))
                            )]
        logger.debug('projectusernames: %s', projectusernames)

        # separate into membership and managerial control
        relation_groups = {entry['relationship']:[] for entry in group_data}
        for entry in group_data:
            relation_groups[entry['relationship']].append(entry)

        logger.debug('relation_groups: %s', relation_groups)
        ### check through membership list ###
        try:
            ad_users = [u['user_name'] for u in relation_groups['MemberOf']]
        except KeyError:
            logger.warning("WARNING: MANAGERS BUT NO USERS LISTED FOR %s", project.title)
            errors['no_users'].append(proj_name)
            ad_users = []
        # check for users not in Coldfront
        not_added = [uname for uname in ad_users if uname not in projectusernames]
        logger.debug('AD users not in ProjectUsers:\n%s', not_added)

        if not_added:
            # find accompanying ifxusers in the system
            ifxusers, missing_users = id_present_missing_users(not_added)
            log_missing('users', missing_users)

            present_users = project.projectuser_set.filter(user__in=ifxusers)
            present_users.update(   role=projectuser_role_user,
                                    status=projectuserstatus_active)
            presentusers_ids = present_users.values_list("user__id")
            missing_projectusers = ifxusers.exclude(id__in=presentusers_ids)
            ProjectUser.objects.bulk_create([ProjectUser(
                                                project=project,
                                                user=user,
                                                role=projectuser_role_user,
                                                status=projectuserstatus_active
                                            )
                                            for user in missing_projectusers
                                ])

        ### check through management list ###
        try:
            ad_managers = [u['user_name'] for u in relation_groups['ManagedBy']]
        except KeyError:
            logger.warning('no active managers for project %s', proj_name)
            print(f'WARNING: no active managers for project {proj_name}')
            errors['no_managers'].append(proj_name)
            continue

        # get accompanying ProjectUser entries
        project_managers = project.projectuser_set.filter(user__username__in=ad_managers)
        project_managers.update(role=projectuser_role_manager)

        ### change statuses of inactive ProjectUsers to 'Removed' ###
        projusers_to_remove = [uname for uname in projectusernames if uname not in ad_users]
        if projusers_to_remove:
            # log removed users
            logger.debug('users to remove: %s', projusers_to_remove)

            # if ProjectUser is still an AllocationUser, change to Pending - Remove
            for username in projusers_to_remove:
                project_user = project.projectuser_set.get(user__username=username)
                activeallocationusership = AllocationUser.objects.filter(
                                            allocation__project=project,
                                            user=project_user.user,
                                            status__name__in=['Active', 'Pending - Add']
                                            )
                if activeallocationusership:
                    message = f'cannot remove User {username} for Project {project.title} - active AllocationUser'
                    logger.warning(message)
                    print(message)
                    project_user.update(status=projectuserstatus_pendremove)
                else:
                    project_user.update(status=projectuserstatus_removed)
                    logger.debug('removed User %s from Project %s', username, project.title)

    logger.warning('errorlist: %s', errors)


def generate_headers(token):
    '''Generate 'headers' attribute by using the 'token' attribute.
    '''
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    return headers

def read_json(filepath):
    logger.debug('read_json for %s', filepath)
    with open(filepath, 'r') as myfile:
        data = json.loads(myfile.read())
    return data
