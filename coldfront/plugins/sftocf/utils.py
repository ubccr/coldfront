import os
import re
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

import requests
from django.utils import timezone

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import (determine_size_fmt,
                                        locate_or_create_dirpath,
                                        read_json,
                                        save_json,
                                        select_one_project_allocation,
                                        id_present_missing_users,
                                        log_missing)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import (Allocation,
                                            AllocationUser,
                                            AllocationAttributeType,
                                            AllocationUserStatusChoice)

datestr = datetime.today().strftime('%Y%m%d')
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'logs/starfish_to_coldfront_{datestr}.log', 'w')
logger.addHandler(filehandler)

STARFISH_SERVER = import_from_settings('STARFISH_SERVER')
svp = read_json('coldfront/plugins/sftocf/servers.json')


def record_process(func):
    '''Wrapper function for logging'''
    def call(*args, **kwargs):
        funcdata = '{} {}'.format(func.__name__, func.__code__.co_firstlineno)
        logger.debug('\n%s START.', funcdata)
        result = func(*args, **kwargs)
        logger.debug('%s END. output:\n%s\n', funcdata, result)
        return result
    return call


class StarFishServer:
    '''Class for interacting with StarFish API.
    '''

    def __init__(self, server):
        self.name = server
        self.api_url = f'https://{server}.rc.fas.harvard.edu/api/'
        self.token = self.get_auth_token()
        self.headers = generate_headers(self.token)
        self.volumes = self.get_volume_names()

    @record_process
    def get_auth_token(self):
        '''Obtain a token through the auth endpoint.
        '''
        username = import_from_settings('SFUSER')
        password = import_from_settings('SFPASS')
        auth_url = self.api_url + 'auth/'
        todo = {'username': username, 'password': password}
        response = requests.post(auth_url, json=todo)
        # response.status_code
        response_json = response.json()
        token = response_json['token']
        return token


    # 2A. Generate list of volumes to search, along with top-level paths
    @record_process
    def get_volume_names(self):
        ''' Generate a list of the volumes available on the server.
        '''
        url = self.api_url + 'storage/'
        response = return_get_json(url, self.headers)
        volnames = [i['name'] for i in response['items']]
        return volnames

    def get_volume_attributes(self):
        url = self.api_url + 'volume/'
        response = return_get_json(url, self.headers)
        return response

    def get_tags(self):
        url = self.api_url + 'tag/'
        response = return_get_json(url, self.headers)
        return response

    def make_tags(self):
        # get list of existing tags
        tags = self.get_tags()

    def get_scan_date(self, volume):
        '''See the date of the last completed scan of a given volume
        '''

    @record_process
    def get_subpaths(self, volpath):
        '''Generate list of directories in top layer of designated volpath.

        Parameters
        ----------
        volpath : string
            The volume and path.

        Returns
        -------
        subpaths : list of strings
        '''
        getsubpaths_url = self.api_url + 'storage/' + volpath
        request = return_get_json(getsubpaths_url, self.headers)
        pathdicts = request['items']
        subpaths = [i['Basename'] for i in pathdicts]
        return subpaths

    def create_query(self, query, group_by, volpath, sec=3):
        '''Produce a Query class object.
        Parameters
        ----------
        query : string
        group_by : string
        volpath : string
        sec : integer, optional

        Returns
        -------
        query : Query class object
        '''
        query = StarFishQuery(
            self.headers, self.api_url, query, group_by, volpath, sec=sec
        )
        return query

    @record_process
    def get_vol_membership(self, volume, voltype):
        url = self.api_url + f'mapping/{voltype}_membership?volume_name=' + volume
        member_list = return_get_json(url, self.headers)
        return member_list

    @record_process
    def get_vol_user_name_ids(self, volume):
        usermap_url = self.api_url + 'mapping/user?volume_name=' + volume
        users = return_get_json(usermap_url, self.headers)
        userdict = {u['uid']: u['name'] for u in users}
        return userdict

    @record_process
    def get_starfish_groups(self):
        url = f'{self.api_url}mapping/user_membership'
        group_dict = return_get_json(url, self.headers)
        group_list = [g['name'] for g in group_dict]
        return group_list


class StarFishRedash:
    def __init__(self, server_name):
        self.base_url = f'https://{server_name}.rc.fas.harvard.edu/redash/api/'
        self.queries = import_from_settings('REDASH_API_KEYS')


    def return_present_absent_allocations(self):
        '''Divide Starfish redash subdirectory query results by presence of
        allocation in Coldfront.
        Only counts allocations that also have projects in
        '''
        data = self.return_cleaned_allocation_results()
        allocations = [(a.project.title, a.resources.first().name.split('/')[0], a.path)
                        for a in Allocation.objects.all()]
        starfish_allocations = [(a['group_name'],a['vol_name'], a['path'])
                        for a in data]

        present_by_path = [a for a in starfish_allocations if any(a[1]==b[1] and a[2]==b[2] for b in allocations)]
        absent_by_path = [a for a in starfish_allocations if not any(a[1]==b[1] and a[2]==b[2] for b in allocations)]
        absent_by_path_or_group = [a for a in absent_by_path if not any(a[1]==b[1] and a[0]==b[0] for b in allocations)]
        absent_clustered = []


    def submit_query(self, queryname):
        query = self.queries[queryname]
        query_url = f'{self.base_url}queries/{query[0]}/results?api_key={query[1]}'
        result = return_get_json(query_url, headers={})
        return result


    def get_vol_stats(self):
        result = self.submit_query('vol_query')
        result = result['query_result']['data']['rows']
        result = [{k.replace(' ', '_').replace('(','').replace(')','') : v for k, v in d.items()} for d in result]
        resource_names = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name',flat=True)]
        result = [r for r in result if r['volume_name'] in resource_names]
        return result


    def get_usage_stats(self, query='path_usage_query', volumes=None):
        '''
        '''
        result = self.submit_query(query)
        # print(result)
        if result['query_result']:
            data = result['query_result']['data']['rows']
        else:
            print("no query_result value found:\n", result)
        if volumes:
            data = [d for d in data if d['vol_name'] in volumes]

        return data


class StarFishQuery:
    def __init__(self, headers, api_url, query, group_by, volpath, sec=3):
        self.api_url = api_url
        self.headers = headers
        self.query_id = self.post_async_query(query, group_by, volpath)
        self.result = self.return_results_once_prepared(sec=sec)


    @record_process
    def post_async_query(self, query, group_by, volpath, q_format='parent_path +rec_aggrs'):
        query_url = self.api_url + 'async/query/'

        params = {
            'volumes_and_paths': volpath,
            'queries': query,
            'format': q_format,
            'sort_by': group_by,
            'group_by': group_by,
            'limit': '100000',
            'force_tag_inherit': 'false',
            'output_format': 'json',
            'delimiter': ',',
            'escape_paths': 'false',
            'print_headers': 'true',
            'size_unit': 'B',
            'humanize_nested': 'false',
            'mount_agent': 'None',
        }
        r = requests.post(query_url, params=params, headers=self.headers)
        response = r.json()
        logger.debug('response: %s', response)
        return response['query_id']

    @record_process
    def return_results_once_prepared(self, sec=3):
        while True:
            query_check_url = self.api_url + 'async/query/' + self.query_id
            response = return_get_json(query_check_url, self.headers)
            if response['is_done'] == True:
                result = self.return_query_result()
                return result
            time.sleep(sec)

    def return_query_result(self):
        query_result_url = self.api_url + 'async/query_result/' + self.query_id
        response = return_get_json(query_result_url, self.headers)
        return response


@record_process
def produce_lab_dict(vol):
    '''Create dict of labs to collect and the volumes/tiers associated with them.
    Parameters
    ----------
    vol : string
        If not None, collect only allocations on the specified volume

    Returns
    -------
    labs_resources: dict
        Structured as follows:
        'lab_name': [('volume', 'tier'),('volume', 'tier')]
    '''
    pr_objs = Allocation.objects.only('id', 'project')
    pr_dict = {}
    for alloc in pr_objs:
        proj_name = alloc.project.title
        resource_list = alloc.get_resources_as_string.split(', ')
        if proj_name not in pr_dict:
            pr_dict[proj_name] = resource_list
        else:
            pr_dict[proj_name].extend(resource_list)
    lr = pr_dict if not vol else {p:[i for i in r if vol in i] for p, r in pr_dict.items()}
    labs_resources = {p:[tuple(rs.split('/')) for rs in r] for p, r in lr.items()}
    return labs_resources


def check_volume_collection(lr, homepath='./coldfront/plugins/sftocf/data/'):
    '''
    for each lab-resource combination in parameter lr, check existence of
    corresponding file in data path. If a file for that lab-resource combination
    that is <2 days old exists, mark it as collected. If not, slate lab-resource
    combination for collection.

    Parameters
    ----------
    lr : dict
        Keys are labnames, values are a list of (volume, tier) tuples.

    Returns
    -------
    filepaths : list
        List of lab usage files that have already been created.
    to_collect : list
        list of tuples - (labname, volume, tier, filename)
    '''
    filepaths = []
    to_collect = []
    labs_resources = [(l, res[0], res[1]) for l, r in lr.items() for res in r]

    yesterdaystr = (datetime.today()-timedelta(1)).strftime('%Y%m%d')
    dates = [yesterdaystr, datestr]

    for lr_pair in labs_resources:
        lab = lr_pair[0]
        resource = lr_pair[1]
        tier = lr_pair[2]
        fpaths = [f'{homepath}{lab}_{resource}_{n}.json' for n in dates]
        if any(Path(fpath).exists() for fpath in fpaths):
            for fpath in fpaths:
                if Path(fpath).exists():
                    filepaths.append(fpath)
        else:
            to_collect.append((lab, resource, tier, fpaths[-1],))

    return filepaths, to_collect


def pull_sf(volume=None):
    '''Query Starfish to produce json files of lab usage data.
    Return a set of produced filepaths.
    '''
    # 1. produce dict of all labs to be collected and the volumes on which their data is located
    lr = produce_lab_dict(volume)
    # 2. produce list of files that have been collected and list of lab/volume/filename tuples to collect
    filepaths, to_collect = check_volume_collection(lr)
    # 3. produce set of all volumes to be queried
    vol_set = {i[1] for i in to_collect}
    servers_vols = [(k, vol) for k, v in svp.items() for vol in vol_set if vol in v.keys()]
    for server_vol in servers_vols:
        s = server_vol[0]
        vol = server_vol[1]
        paths = svp[s][vol]
        to_collect_subset = [t for t in to_collect if t[1] == vol]
        logger.debug('vol:%s\nto_collect_subset:%s', vol, to_collect_subset)
        server = StarFishServer(s)
        fpaths = collect_starfish_usage(server, vol, paths, to_collect_subset)
        filepaths.extend(fpaths)
    return set(filepaths)


def push_cf(filepaths, clean):
    for f in filepaths:
        errors = False
        content = read_json(f)
        usernames = [d['username'] for d in content['contents']]
        resource = content['volume'] + '/' + content['tier']

        user_models, missing_usernames = id_present_missing_users(usernames)
        log_missing('user', missing_usernames)

        project = Project.objects.get(title=content['project'])
        # find project allocation
        allocation = select_one_project_allocation(project, resource)
        logger.debug('%s\n usernames: %s\n user_models: %s',
                project.title, usernames, [u.username for u in user_models])

        for user in user_models:
            userdict = next(d for d in content['contents'] if d['username'] == user.username)
            model = user_models.get(username=userdict['username'])
            try:
                update_usage(model, userdict, allocation)
            except Exception as e:
                logger.warning('EXCEPTION FOR ENTRY: %s', e, exc_info=True)
                errors = True
        if not errors and clean:
            os.remove(f)
    logger.debug('push_cf complete')


def update_usage(user, userdict, allocation):
    usage, unit = split_num_string(userdict['size_sum_hum'])
    logger.debug('entering for user: %s', user.username)
    allocationuser, created = allocation.allocationuser_set.get_or_create(
            user=user,
            defaults={
                "created": timezone.now(),
                "status": AllocationUserStatusChoice.objects.get(name='Active')
                }
            )
    if created:
        logger.info('allocation user %s created', allocationuser)
    allocationuser.update(  usage_bytes = userdict['size_sum'],
                            usage = usage,
                            unit = unit)


def split_num_string(x):
    n = re.search(r'\d*\.?\d+', x).group()
    s = x.replace(n, '')
    return n, s

def return_get_json(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()


@record_process
def collect_starfish_usage(server, volume, volumepath, projects):
    '''
    Parameters
    ----------
    server : object
    volume : string
    volumepath : list of strings
    projects : list of tuples

    Returns
    -------
    filepaths : list of strings
    '''
    filepaths = []
    datestr = datetime.today().strftime('%Y%m%d')
    locate_or_create_dirpath('./coldfront/plugins/sftocf/data/')

    ### OLD METHOD ###
    for t in projects:
        p = t[0]
        tier = t[2]
        filepath = t[3]
        lab_volpath = volumepath[0] if '_l3' not in p else volumepath[1]
        logger.debug('filepath: %s lab: %s volpath: %s', filepath, p, lab_volpath)
        usage_query = server.create_query(
            f'groupname={p} type=d', 'volume,parent_path,username,groupname,rec_aggrs.size,fn', f'{volume}:{lab_volpath}'
        )
        data = usage_query.result
        if not data:
            logger.warning('No starfish result for lab %s', p)

        elif type(data) is dict and 'error' in data:
            logger.warning('Error in starfish result for lab %s:\n%s', p, data)
        else:
            data = usage_query.result
            data = clean_dirs_data(data)
            record = {
                'server': server.name,
                'volume': volume,
                'path': lab_volpath,
                'project': p,
                'tier': tier,
                'date': datestr,
                'contents': data,
            }
            save_json(filepath, record)
            filepaths.append(filepath)

    return filepaths


def clean_dirs_data(data):
    data = [d for d in data if d['username'] != 'root']
    for entry in data:
        entry['size_sum'] = entry['rec_aggrs']['size']
        entry['full_path'] = entry['parent_path']+'/'+entry['fn']
        for item in ['count', 'size_sum_hum','rec_aggrs','fn','parent_path']:
            entry.pop(item)
    # remove any directory that is a subdirectory of a directory owned by the same user
    users = {d['username'] for d in data}
    data2 = []
    for user in users:
        user_dirs = [d for d in data if d['username'] == user]
        allpaths = [Path(d['full_path']) for d in user_dirs]
        # user_entry = {"groupname":user_dirs[0]['groupname'], "username":user, "size_sum":0}
        for dir_dict in user_dirs:
            path = Path(dir_dict['full_path'])
            if any(p in path.parents for p in allpaths):# or dir_dict['size_sum'] == 0:
                pass
            else:
                data2.append(dir_dict)
                # user_entry['size_sum'] += dir_dict['size_sum']
        # data2.append(user_entry)
    allpaths = [Path(d['full_path']) for d in data2]
    for dir_dict in data2:
        if any(p in path.parents for p in allpaths):
            print("nested:", dir_dict)
    return data2

def generate_headers(token):
    '''Generate 'headers' attribute by using the 'token' attribute.
    '''
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer {}'.format(token),
    }
    return headers

def zero_out_absent_allocationusers(redash_usernames, allocation):
    '''
    Find AllocationUsers that aren't in the StarfishRedash usage
    stats and change their usage to 0.
    '''
    allocationusers = allocation.allocationuser_set.all()
    allocationusers_not_in_redash = allocationusers.exclude(user__username__in=redash_usernames)
    if allocationusers_not_in_redash:
        logger.info('users no longer in allocation %s: %s', allocation.pk, [user.user.username for user in allocationusers_not_in_redash])
        allocationusers_not_in_redash.update(usage=0, usage_bytes=0)

def compare_cf_sf_volumes():
    '''
    cross-reference CF Resources and SF volumes to produce list of all
    volumes to be collected
    '''
    resource_names = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name', flat=True)]
    # limit volumes to be collected to those ones present in the Starfish database
    volume_names = StarFishServer(STARFISH_SERVER).volumes
    vols_to_collect = [vol for vol in volume_names for res in resource_names if vol == res]
    return vols_to_collect


def pull_sf_push_cf_redash(pull_totals=True):
    '''
    Query Starfish Redash API for user usage data and update Coldfront AllocationUser entries.

    Only Projects that are already in Coldfront will get updated.
    '''
    vols_to_collect = compare_cf_sf_volumes()
    # 2. grab data from redash
    redash_api = StarFishRedash(STARFISH_SERVER)
    user_usage = redash_api.get_usage_stats(volumes=vols_to_collect)
    user_usage_by_group = redash_api.get_usage_stats(query='usage_query', volumes=vols_to_collect)
    allocation_usages = redash_api.get_usage_stats(query="subdirectory", volumes=vols_to_collect)
    queryset = []
    issues = {'no_users':[], 'no_total':[], 'no_path':[]}

    # limit allocations to those in the volumes collected
    searched_resources = [Resource.objects.get(name__contains=vol) for vol in vols_to_collect]
    allocation_attribute_types = AllocationAttributeType.objects.all()
    quota_bytes_attributetype = allocation_attribute_types.get(name='Quota_In_Bytes')
    quota_tbs_attributetype = allocation_attribute_types.get(name='Storage Quota (TB)')
    allocations = Allocation.objects.filter(resources__in=searched_resources,
        status__name__in=['Active', 'New', 'Updated', 'Ready for Review'])
    # 3. iterate across allocations
    for allocation in allocations:
        project = allocation.project
        lab = project.title
        resource = allocation.get_parent_resource
        volume = resource.name.split('/')[0]
        logger.debug('adding resource for %s %s (path %s)', lab, resource, allocation.path)

        # select query rows that match allocation volume and lab
        # confirm that only one allocation is represented by checking the path
        if allocation.path:
            lab_data = [i for i in user_usage if i['vol_name'] == volume and allocation.path == i['lab_path']]
            usage_data = [i for i in allocation_usages if i['vol_name'] == volume and allocation.path == i['path']]
        else:
            logger.info('no allocation path for allocation %s / %s; defaulting to membership-based usage reporting.', project, volume)
            issues['no_path'].append((allocation.pk, project, volume))
            lab_data = [i for i in user_usage_by_group if i['vol_name'] == volume and i['group_name'] == lab]
            print(f'no allocation path for allocation {allocation.pk} {project} / {volume}; defaulting to membership-based usage reporting.', allocation.allocationattribute_set.all())
            usage_data = [i for i in allocation_usages if i['vol_name'] == volume and i['group_name'] == lab]

        if pull_totals is False:
            pass
        elif not usage_data:
            print('WARNING: No starfish allocation usage for', allocation.pk, lab, resource)
            logger.warning('WARNING: No starfish allocation usage result for allocation %s %s %s',
                allocation.pk, lab, resource)
            issues['no_total'].append((allocation.pk, project, volume))
        else:
            usage_data = usage_data[0]
            bytes_attribute, _ = allocation.allocationattribute_set.update_or_create(
                    allocation_attribute_type=quota_bytes_attributetype,
                    defaults={'value': usage_data['total_size']}
                )
            tbs = (usage_data['total_size']/1099511627776)
            logger.info('allocation usage for allocation %s: %s bytes, %s terabytes',
                        allocation.pk, usage_data['total_size'], tbs)
            tbs_attribute, _ = allocation.allocationattribute_set.update_or_create(
                    allocation_attribute_type=quota_tbs_attributetype,
                    defaults={'value': tbs })

        if not lab_data:
            print('No starfish user-level results for',allocation.pk, lab, resource)
            logger.warning('WARNING: No starfish user usage result for allocation %s %s %s',
                                                allocation.pk, lab, resource)
            issues['no_users'].append((allocation.pk, project, volume))
            usernames = []
            zero_out_absent_allocationusers(usernames, allocation)
            continue

        usernames = [d['user_name'] for d in lab_data]
        logger.debug('users returned: %s', usernames)

        # identify and record users that aren't in Coldfront
        user_models, missing_usernames = id_present_missing_users(usernames)
        log_missing('user', missing_usernames)
        logger.debug('%d / %d users are present.\nColdfront users: %s',
                len(user_models), len(usernames), [u.username for u in user_models])

        # identify and remove allocation users that are no longer in the AD group
        zero_out_absent_allocationusers(usernames, allocation)

        for user in user_models:
            userdict = next(d for d in lab_data if d['user_name'].lower() == user.username.lower())
            logger.debug('entering for user: %s', user.username)
            allocationuser, created = allocation.allocationuser_set.get_or_create(
                user=user,
                defaults={
                    'status': AllocationUserStatusChoice.objects.get(name='Active'),
                    'created': timezone.now(),
                })
            if created:
                logger.info('allocation user %s created', allocationuser)
            size_sum = int(userdict['size_sum'])
            usage, unit = determine_size_fmt(userdict['size_sum'])

            allocationuser.usage_bytes = size_sum
            allocationuser.usage = usage
            allocationuser.unit = unit
            queryset.append(allocationuser)
            logger.debug('saving %s', userdict)

    AllocationUser.objects.bulk_update(queryset, ['usage_bytes', 'usage', 'unit'])
    logger.warning("issues recorded: %s", issues)
    print(f"issues recorded: {issues}")
