import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

import requests
from ifxbilling.models import Account, BillingRecord, ProductUsage
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import determine_size_fmt
from coldfront.core.project.models import Project, ProjectUser, ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import (Allocation,
                                            AllocationUser,
                                            AllocationUserStatusChoice)

datestr = datetime.today().strftime('%Y%m%d')
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'logs/starfish_to_coldfront_{datestr}.log', 'w')
logger.addHandler(filehandler)

STARFISH_SERVER = "holysfdb01"

with open('coldfront/plugins/sftocf/servers.json', 'r') as myfile:
    svp = json.loads(myfile.read())

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


def get_redash_vol_stats():
    all_results = []
    redash = StarFishRedash()
    for query_id, query_key in redash.queries['volume_query'].items():
        query_url = f'{redash.base_url}queries/{query_id}/results?api_key={query_key}'
        result = return_get_json(query_url, headers={})
        all_results.extend(result['query_result']['data']['rows'])
    all_results = [{k.replace(' ', '_').replace('(','').replace(')','') : v for k, v in d.items()} for d in all_results]
    resource_names = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name', flat=True)]
    all_results = [r for r in all_results if r['volume_name'] in resource_names]
    return all_results


class StarFishRedash:
    def __init__(self, server_name):
        self.base_url = f'https://{server_name}.rc.fas.harvard.edu/redash/api/'
        self.queries = import_from_settings('REDASH_API_KEYS')


    def get_vol_stats(self):
        query = self.queries['vol_query']
        query_url = f'{self.base_url}queries/{query[0]}/results?api_key={query[1]}'
        result = return_get_json(query_url, headers={})['query_result']['data']['rows']
        result = [{k.replace(' ', '_').replace('(','').replace(')','') : v for k, v in d.items()} for d in result]
        resource_names = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name',flat=True)]
        result = [r for r in result if r['volume_name'] in resource_names]
        return result


    def get_usage_stats(self, volumes=None):
        '''
        '''
        query = self.queries['usage_query']
        query_url = f'{self.base_url}queries/{query[0]}/results?api_key={query[1]}'
        result = return_get_json(query_url, headers={})
        # print(result)
        if result['query_result']:
            data = result['query_result']['data']['rows']
        else:
            print("no query_result value found:")
            print(result)
        if volumes:
            result = [d for d in data if d['vol_name'] in volumes]

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
    for each lab-resource combination in parameter lr, check existence of corresponding
    file in data path. If a file for that lab-resource combination that is <2 days old
    exists, mark it as collected. If not, slate lab-resource combination for collection.

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

        user_models = get_user_model().objects.only('id','username')\
                .filter(username__in=usernames)
        log_missing_user_models(content['project'], user_models, usernames)

        project = Project.objects.get(title=content['project'])
        # find project allocation
        try:
            allocation = Allocation.objects.get(project=project, resources__name=resource)
        except Allocation.MultipleObjectsReturned:
            logger.debug('Too many allocations for project id %s; choosing one with "Allocation Information" in justification.',
                                                            project.id)

            # try:
            allocation = Allocation.objects.get(
                project=project,
                resources__name=resource,
                justification__icontains='Allocation Information',
                justification__endswith=project.title)
            # except Allocation.MultipleObjectsReturned:
            #     logger.warning('Too many allocations for project id {project.id}, matching justifications; choosing the first. Fix this duplication.')
            #     allocations = Allocation.objects.filter(
            #         project_id=project.id,
            #         justification__icontains='Allocation Information',
            #         justification__endswith=project.title)
            #     for a in allocations:
            #         logger.warning(f'Duplicate item:{a}')
            #     allocation = allocations.first()
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
    try:
        allocationuser = AllocationUser.objects.get(
            allocation=allocation, user=user
        )
    except AllocationUser.DoesNotExist:
        logger.info('creating allocation user:')
        AllocationUser.objects.create(
            allocation=allocation,
            created=timezone.now(),
            status=AllocationUserStatusChoice.objects.get(name='Active'),
            user=user
        )
        allocationuser = AllocationUser.objects.get(
            allocation=allocation, user=user
        )

    allocationuser.usage_bytes = userdict['size_sum']
    allocationuser.usage = usage
    allocationuser.unit = unit
    # automatically updates 'modified' field & adds old record to history
    try:
        allocationuser.save()
        logger.debug('successful entry: %s, %s', userdict['groupname'], userdict['username'])
    except ValidationError:
        logger.warning("no ProjectUser entry for %s %s", userdict['groupname'], userdict['username'])
        fpath = './coldfront/plugins/sftocf/data/missing_projectusers.csv'
        patterns = [f'{userdict["groupname"]},{userdict["username"]},{datestr}' for uname in missing_unames]
        write_update_file_line(fpath, patterns)



def clean_data_dir(homepath):
    '''Remove json from data folder that's more than a week old
    '''
    files = os.listdir(homepath)
    json_files = [f for f in files if '.json' in f]
    now = time.time()
    for f in json_files:
        fpath = f'{homepath}{f}'
        created = os.stat(fpath).st_ctime
        if created < now - 7 * 86400:
            os.remove(fpath)

def write_update_file_line(filepath, patterns):
    with open(filepath, 'a+') as f:
        f.seek(0)
        for pattern in patterns:
            if not any(pattern == line.rstrip('\r\n') for line in f):
                f.write(pattern + '\n')

def split_num_string(x):
    n = re.search(r'\d*\.?\d+', x).group()
    s = x.replace(n, '')
    return n, s

def return_get_json(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()

def save_json(file, contents):
    with open(file, 'w') as fp:
        json.dump(contents, fp, sort_keys=True, indent=4)

def read_json(filepath):
    logger.debug('read_json for %s', filepath)
    with open(filepath, 'r') as json_file:
        data = json.loads(json_file.read())
    return data

def locate_or_create_dirpath(dpath):
    if not os.path.exists(dpath):
        os.makedirs(dpath)
        logger.info('created new directory %s', dpath)

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


def log_missing_user_models(groupname, user_models, usernames):
    '''Identify and record any usernames that lack a matching user_models entry.
    '''
    missing_unames = [u for u in usernames if u not in [m.username for m in user_models]]
    if missing_unames:
        fpath = './coldfront/plugins/sftocf/data/missing_ifxusers.csv'
        patterns = [f'{groupname},{uname},{datestr}' for uname in missing_unames]
        write_update_file_line(fpath, patterns)
        logger.warning('no IfxUser found for users: %s', missing_unames)


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

def pull_sf_push_cf_redash():
    '''
    Query Starfish Redash API for user usage data and update Coldfront AllocationUser entries.

    Only Projects that are already in Coldfront will get updated.

    Assumptions this code relies on:
    1. A project cannot have multiple allocations on the same storage resource.
    '''

    # 1. cross-reference CF Resources and SF volumes to produce list of all
    #    volumes to be collected

    resource_names = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name', flat=True)]
    # limit volumes to be collected to those ones present in the Starfish database
    volume_names = StarFishServer(STARFISH_SERVER).volumes
    vols_to_collect = [vol for vol in volume_names for res in resource_names if vol == res]
    # 2. grab data from redash
    redash_api = StarFishRedash(STARFISH_SERVER)
    user_usage = redash_api.get_usage_stats(volumes=vols_to_collect)
    queryset = []

    # limit allocations to those in the volumes collected
    searched_resources = [Resource.objects.get(name__contains=vol) for vol in vols_to_collect]
    allocations = Allocation.objects.filter(resources__in=searched_resources)

    # 3. iterate across allocations
    for allocation in allocations:
        project = allocation.project
        lab = project.title
        resource = allocation.get_parent_resource
        volume = resource.name.split('/')[0]

        # select query rows that match allocation volume and lab
        lab_data = [i for i in user_usage if i['group_name'] == lab and i['vol_name'] == volume]
        if not lab_data:
            print('No starfish result for', lab, resource)
            logger.warning('WARNING: No starfish result for %s %s', lab, resource)
            continue

        usernames = [d['user_name'] for d in lab_data]

        user_models = get_user_model().objects.filter(username__in=usernames)
        log_missing_user_models(lab, user_models, usernames)
        logger.debug('%s\n usernames: %s\n user_models: %s',
                project.title, usernames, [u.username for u in user_models])

        for user in user_models:
            userdict = next(d for d in lab_data if d['user_name'].lower() == user.username.lower())
            logger.debug('entering for user: %s', user.username)
            try:
                allocationuser = AllocationUser.objects.get(
                    allocation=allocation, user=user
                )
            except AllocationUser.DoesNotExist:
                if userdict['size_sum'] > 0:
                    try:
                        allocationuser = AllocationUser.objects.create(
                            allocation=allocation,
                            created=timezone.now(),
                            status=AllocationUserStatusChoice.objects.get(name='Active'),
                            user=user
                        )
                    except ValidationError:
                        logger.warning("no ProjectUser entry for %s %s", userdict['group_name'], userdict['user_name'])
                        fpath = './coldfront/plugins/sftocf/data/missing_projectusers.csv'
                        pattern = f'{userdict["group_name"]},{userdict["user_name"]},{datestr}'
                        write_update_file_line(fpath, [pattern])
                        continue
                else:
                    logger.warning("allocation user missing: %s %s %s", lab, resource, userdict)
                    continue
            size_sum = int(userdict['size_sum'])
            usage, unit = determine_size_fmt(userdict['size_sum'])
            allocationuser.usage_bytes = size_sum
            allocationuser.usage = usage
            allocationuser.unit = unit
            queryset.append(allocationuser)
            # automatically update 'modified' field & add old record to history
            logger.debug("saving %s",userdict)
    AllocationUser.objects.bulk_update(queryset, ['usage_bytes', 'usage', 'unit'])
