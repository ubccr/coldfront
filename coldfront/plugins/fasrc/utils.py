import json
import logging
import operator
from functools import reduce
from datetime import datetime

import requests
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone

from coldfront.core.utils.common import import_from_settings
from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.fasrc import (log_missing,
                                        id_present_missing_users,
                                        id_present_missing_resources,
                                        id_present_missing_projects)
from coldfront.core.project.models import ( Project,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice,
                                            ProjectStatusChoice,
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

def change_filehandler(filepath):
    '''change logger filehandler'''
    logger.removeHandler(filehandler)
    handler = logging.FileHandler(filepath, 'w')
    logger.addHandler(handler)


def record_process(func):
    '''Wrapper function for logging'''
    def call(*args, **kwargs):
        funcdata = '{} {}'.format(func.__name__, func.__code__.co_firstlineno)
        logger.debug('\n%s START.', funcdata)
        result = func(*args, **kwargs)
        logger.debug('%s END. output:\n%s\n', funcdata, result)
        return result
    return call

class ErrorTracker:
    '''class for tracking errors that arise when processing groupuser data'''
    def __init__(self):
        self.no_members = []
        self.no_users = []
        self.no_managers = []

    def report(self):
        '''report errors'''
        logger.warning('AD groups with no members: %s', self.no_members)
        logger.warning('AD groups with no users: %s', self.no_users)
        logger.warning('AD groups with no managers: %s', self.no_managers)


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
        Collect user, and relationship information for a given lab or labs from ATT.
        '''
        query = {'statements': [{
                    'statement': f'MATCH (u:User)-[r:MemberOf|ManagedBy]-(g:Group) \
                    WHERE (g.ADSamAccountName =~ \'{groupname}\') \
                    RETURN \
                    u.ADgivenName AS first_name, \
                    u.ADsurname AS last_name, \
                    u.ADSamAccountName AS user_name, \
                    u.ADenabled AS user_enabled, \
                    g.ADSamAccountName AS group_name,\
                    type(r) AS relationship,\
                    g.ADManaged_By AS group_manager, \
                    u.ADgidNumber AS user_gid_number, \
                    g.ADgidNumber AS group_gid_number'
                }]}
        resp_json = self.post_query(query)
        resp_json_formatted = self.format_query_results(resp_json)
        return resp_json_formatted

    def collect_pi_data(self, grouplist):
        '''collect information on pis for a given list of groups
        '''
        groupnamesearch = "|".join(grouplist)
        query = {'statements': [{
                    'statement': f'MATCH (g:Group)\
                    WITH g\
                    MATCH (u:User)\
                    WHERE (g.ADSamAccountName =~ \'({groupnamesearch})\') \
                    AND u.ADSamAccountName = g.ADManaged_By\
                    RETURN\
                    g.ADSamAccountName AS group_name,\
                    u.ADSamAccountName AS user_name, \
                    u.ADgivenName AS first_name, \
                    u.ADsurname AS last_name, \
                    u.ADmail AS email, \
                    u.ADDepartment AS department, \
                    u.ADTitle AS title, \
                    u.ADCompany AS company, \
                    u.ADParentCanonicalName AS path, \
                    u.DotsPTLUpdateDate, \
                    u.DotsADUpdateDate, \
                    u.ADenabled AS user_enabled, \
                    u.NANInNanites AS in_nanites, \
                    u.ADgidNumber AS user_gid_number'
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
            'where':f"(e.Isilon =~ '.*({volumes}).*') AND r.DotsUpdateDate = d.DotsUpdateDate",
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
                    AND NOT (g.ADSamAccountName =~ '.*(disabled|rc_admin).*')\
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
        with open(result_file, 'w') as file:
            file.write(json.dumps(resp_json_by_lab_cleaned, indent=2))
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

        for k, v in result_json.items():
            result_json[k] = [a for a in v if a['server'] not in missing_res]

        for lab, allocations in result_json.items():
            logger.debug('PROJECT: %s ====================================', lab)
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
                    a = Allocation.objects.filter(  project=proj_query,
                                                    resources__id=resource.id,
                                                    status__name='Active'   )
                    if a.count() == 1:
                        a = a.first()
                    elif a.count() < 1:
                        logger.warning("ERROR: No Allocation for project %s, resource %s",
                                                    proj_query.title, resource.name)
                        missing_allocations.append({
                                "resource_name":resource.name,
                                "project_title": proj_query.title
                                })
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

                    logger.info("allocation: %s", a.__dict__)

                    # 4. get the storage quota TB allocation_attribute that has allocation=a.
                    allocation_values = { 'Storage Quota (TB)':
                                [allocation['tb_allocation'],allocation['tb_usage']]  }
                    if allocation['byte_allocation'] != None:
                        allocation_values['Quota_In_Bytes'] = [ allocation['byte_allocation'],
                                                    allocation['byte_usage']]

                    for k, v in allocation_values.items():
                        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                            name=k)
                        try:
                            allocation_attribute_obj = AllocationAttribute.objects.get(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                allocation=a,
                            )
                            allocation_attribute_obj.value = v[0]
                            allocation_attribute_obj.save()
                            allocation_attribute_exist = True
                        except AllocationAttribute.DoesNotExist:
                            allocation_attribute_exist = False

                        if (not allocation_attribute_exist):
                            allocation_attribute_obj,_ =AllocationAttribute.objects.get_or_create(
                                allocation_attribute_type=allocation_attribute_type_obj,
                                allocation=a,
                                value = v[0])
                            allocation_attribute_type_obj.save()

                        allocation_attribute_obj.allocationattributeusage.value = v[1]
                        allocation_attribute_obj.allocationattributeusage.save()

                    # 5. AllocationAttribute
                    allocation_attribute_type_payment = AllocationAttributeType.objects.get(name='RequiresPayment')
                    allocation_attribute_payment, _ = AllocationAttribute.objects.get_or_create(
                            allocation_attribute_type=allocation_attribute_type_payment,
                            allocation=a,
                            value=True)
                    allocation_attribute_payment.save()
                    counts['complete'] += 1
                except Exception as e:
                    allocation_name = f"{allocation['lab']}/{allocation['server']}"
                    errored_allocations[allocation_name] = e
        log_missing("allocation", missing_allocations)
        logger.warning("error counts: %s", counts)
        logger.warning('errored_allocations:\n%s', errored_allocations)


def create_new_projects(projects_list: list, dryrun=False):
    '''
    Use ATT user, group, and relationship information to automatically create new
    Coldfront Projects from projects_list.
    '''
    change_filehandler(f'logs/{today}_projectcreation_att.log')

    att_conn = AllTheThingsConn()
    errortracker = ErrorTracker()
    # if project already exists, end here
    existing_projects = Project.objects.filter(title__in=projects_list)
    if existing_projects:
        logger.debug("existing projects: %s", [p.title for p in existing_projects])
    projects_to_add = [p for p in projects_list if p not in [p.title for p in existing_projects]]

    # if PI is inactive or otherwise unavailable, don't add project or users
    pi_data = att_conn.collect_pi_data(projects_to_add)
    no_active_pis = [entry['group_name'] for entry in pi_data if not entry['user_enabled']]
    logger.debug("projects lacking active PIs: %s", no_active_pis)
    missing_pi_usernames = [entry['user_name'] for entry in pi_data if not entry['user_enabled']]
    active_pi_groups = [entry for entry in pi_data if entry['user_enabled']]

    # bulk-query user/group data
    user_group_search = "|".join(entry['group_name'] for entry in active_pi_groups)
    aduser_data = att_conn.collect_group_membership(f"({user_group_search})")
    aduser_data = [user for user in aduser_data if user['user_enabled']]

    # log and remove from list any AD users not in Coldfront
    aduser_names = [u['user_name'] for u in aduser_data]
    _, missing_users = id_present_missing_users(aduser_names)
    log_missing('user', missing_users+missing_pi_usernames)
    aduser_data = [u for u in aduser_data if u['user_name'] not in missing_users]

    for entry in active_pi_groups:
        # collect group membership entries
        ad_members = [user for user in aduser_data if user['group_name'] == entry['group_name']]

        # if no active group members, log and don't add Project
        if not ad_members:
            errortracker.no_members.append(entry['group_name'])
            logger.warning("no members for %s; not adding.", entry['group_name'])
            continue

        ad_managers = [u['user_name'] for u in ad_members if u['relationship'] == 'ManagedBy']
        # if no active managers, log and don't add Project
        if not ad_managers:
            logger.warning('no active managers for project %s', entry['group_name'])
            print(f'WARNING: no active managers for project {entry["group_name"]}')
            errortracker.no_managers.append(entry['group_name'])
            continue


        # locate PI User entry
        try:
            project_pi = get_user_model().objects.get(username=entry['user_name'])
        except get_user_model().DoesNotExist:
            logger.warning('pi for project %s not in ifxusers; skipping', entry['group_name'])
            errortracker.no_managers.append(entry['group_name'])
            continue


        # create description
        description = "Allocations for " + entry['group_name']

        # locate field_of_science
        field_of_science_name=entry['department']

        field_of_science_obj, created = FieldOfScience.objects.get_or_create(
                        description=field_of_science_name,
                        defaults={'is_selectable':'True'}
                        )
        if created:
            logger.info('added new field_of_science: %s', field_of_science_name)


        ### CREATE PROJECT ###
        current_dt = datetime.now(tz=timezone.utc)
        new_project = Project.objects.create(
            created=current_dt,
            modified=current_dt,
            title=entry['group_name'],
            pi=project_pi,
            description=description.strip(),
            field_of_science=field_of_science_obj,
            requires_review=False,
            status=ProjectStatusChoice.objects.get(name='New')
        )

        ### add projectusers ###
        # use set comprehension to avoid duplicate entries when MemberOf/ManagedBy relationships both exist
        ad_member_usernames = {u['user_name'] for u in ad_members}
        users_to_add = get_user_model().objects.filter(username__in=ad_member_usernames)
        new_projectusers = [
            ProjectUser(
                project=new_project,
                user=user,
                status=ProjectUserStatusChoice.objects.get(name='Active'),
                role=ProjectUserRoleChoice.objects.get(name='User'),
                )
            for user in users_to_add
            ]
        added_projectusers = ProjectUser.objects.bulk_create(new_projectusers)

        # add permissions to PI/manager-status ProjectUsers
        manager_usernames = ad_managers + [entry['user_name']]
        for username in manager_usernames:
            logger.debug('adding manager status to ProjectUser %s for Project %s',
                        username, entry['group_name'])
            manager = ProjectUser.objects.get(  project=new_project,
                                                user__username=username)
            manager.role = ProjectUserRoleChoice.objects.get(name='Manager')
            manager.save()

    errortracker.report()


def update_group_membership():
    '''
    Use ATT's user, group, and relationship information to keep the ProjectUser
    list up-to-date for existing Coldfront Projects.
    '''

    # change logger filehandler
    change_filehandler(f'logs/att_membership_update-{today}.log')
    no_members = []
    no_users = []
    no_managers = []

    for project in Project.objects.filter(status__name__in=["Active", "New"]):
        # pull membership data for the given project
        proj_name = project.title
        att_conn = AllTheThingsConn()
        logger.debug('updating group membership for %s', proj_name)
        group_data = att_conn.collect_group_membership(proj_name)
        logger.debug('raw AD group data:\n%s', group_data)
        group_data = [group for group in group_data if group['user_enabled'] is True]
        if not group_data:
            no_members.append(proj_name)
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
            no_users.append(proj_name)
            ad_users = []
        # check for users not in Coldfront
        not_added = [uname for uname in ad_users if uname not in projectusernames]
        logger.debug('AD users not in ProjectUsers:\n%s', not_added)

        if not_added:
            # find accompanying ifxusers in the system
            ifxusers, missing_users = id_present_missing_users(not_added)
            log_missing('users', missing_users)

            for user in ifxusers:
                # in case user is being re-added to the project, first find/create a
                # project_user matching just project/user, then change role & status
                try:
                    project_user = ProjectUser.objects.get(project=project,
                                user=user)
                    project_user.role=ProjectUserRoleChoice.objects.get(name='User')
                    project_user.status = ProjectUserStatusChoice.objects.get(name='Active')
                    project_user.save()
                except ProjectUser.DoesNotExist:
                    ProjectUser.objects.create(project=project,
                                user=user,
                                role=ProjectUserRoleChoice.objects.get(name='User'),
                                status = ProjectUserStatusChoice.objects.get(name='Active')
                                )

        ### check through management list ###
        try:
            ad_managers = [u['user_name'] for u in relation_groups['ManagedBy']]
        except KeyError:
            logger.warning('no active managers for project %s', proj_name)
            print(f'WARNING: no active managers for project {proj_name}')
            no_managers.append(proj_name)
            continue

        # get accompanying ProjectUser entries
        project_managers = ProjectUser.objects.filter(project=project, user__username__in=ad_managers)
        for manager in project_managers:
            # if ProjectUser's role__name is 'User', change it to 'Manager'
            if manager.role.name == 'User':
                manager.role = ProjectUserRoleChoice.objects.get(name='Manager')
                manager.save()

        ### change statuses of inactive ProjectUsers to 'Removed' ###
        projusers_to_remove = [uname for uname in projectusernames if uname not in ad_users]
        if projusers_to_remove:
            # log removed users
            logger.debug('users to remove: %s', projusers_to_remove)

            # if ProjectUser is still an AllocationUser, change to Pending - Remove
            for username in projusers_to_remove:
                project_user = ProjectUser.objects.get( project=project,
                                                        user__username=username)
                activeallocationusership = AllocationUser.objects.filter(
                                            allocation__project=project,
                                            user=project_user.user,
                                            status__name__in=['Active', 'Pending - Add']
                                            )
                if activeallocationusership:
                    message = f'cannot remove User {username} for Project {project.title} - active AllocationUser'
                    logger.warning(message)
                    print(message)
                    project_user.status = ProjectUserStatusChoice.objects.get(name='Pending - Remove')
                else:
                    project_user.status = ProjectUserStatusChoice.objects.get(name='Removed')
                    logger.debug('removed User %s from Project %s', username, project.title)
                project_user.save()
    logger.warning('AD groups with no members: %s', no_members)
    logger.warning('AD groups with no users: %s', no_users)
    logger.warning('AD groups with no managers: %s', no_managers)


def generate_headers(token):
    '''Generate 'headers' attribute by using the 'token' attribute.
    '''
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token),
    }
    return headers

def read_json(filepath):
    logger.debug('read_json for %s', filepath)
    with open(filepath, 'r') as myfile:
        data = json.loads(myfile.read())
    return data
