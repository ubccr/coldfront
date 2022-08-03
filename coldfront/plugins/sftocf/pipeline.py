import os
import re
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta

from django.utils import timezone
from ifxuser.models import IfxUser, Organization
from django.contrib.auth import get_user_model
from ifxbilling.models import Account, BillingRecord, ProductUsage

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.allocation.models import (Allocation, 
                                            AllocationUser, 
                                            AllocationAttribute, 
                                            AllocationUserStatusChoice)

datestr = datetime.today().strftime("%Y%m%d")
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'coldfront/plugins/sftocf/data/logs/sfc{datestr}.log', 'w')
logger.addHandler(filehandler)


with open("coldfront/plugins/sftocf/servers.json", "r") as myfile:
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

class StarFishServer:
    """Class for interacting with StarFish API.
    """

    def __init__(self, server):
        self.name = server
        self.api_url = f"https://{server}.rc.fas.harvard.edu/api/"
        self.token = self.get_auth_token()
        self.headers = generate_headers(self.token)
        self.volumes = self.get_volume_names()

    @record_process
    def get_auth_token(self):
        """Obtain a token through the auth endpoint.
        """
        username = import_from_settings('SFUSER')
        password = import_from_settings('SFPASS')
        auth_url = self.api_url + "auth/"
        todo = {"username": username, "password": password}
        response = requests.post(auth_url, json=todo)
        # response.status_code
        response_json = response.json()
        token = response_json["token"]
        return token


    # 2A. Generate list of volumes to search, along with top-level paths
    @record_process
    def get_volume_names(self):
        """ Generate a list of the volumes available on the server.
        """
        stor_url = self.api_url + "storage/"
        response = return_get_json(stor_url, self.headers)
        volnames = [i["name"] for i in response["items"]]
        return volnames

    @record_process
    def get_subpaths(self, volpath):
        """Generate list of directories in top layer of designated volpath.
        Parameters
        ----------
        volpath : string
            The volume and path.
        Returns
        -------
        subpaths : list of strings
        """
        getsubpaths_url = self.api_url + "storage/" + volpath
        request = return_get_json(getsubpaths_url, self.headers)
        pathdicts = request["items"]
        subpaths = [i["Basename"] for i in pathdicts]
        return subpaths

    def create_query(self, query, group_by, volpath, sec=3):
        """Produce a Query class object.
        Parameters
        ----------
        query : string
        group_by : string
        volpath : string
        sec : integer, optional

        Returns
        -------
        query : Query class object
        """
        query = StarFishQuery(
            self.headers, self.api_url, query, group_by, volpath, sec=sec
        )
        return query

    @record_process
    def get_vol_membership(self, volume, type):
        url = self.api_url + f"mapping/{type}_membership?volume_name=" + volume
        member_list = return_get_json(url, self.headers)
        return member_list

    @record_process
    def get_vol_user_name_ids(self, volume):
        usermap_url = self.api_url + "mapping/user?volume_name=" + volume
        users = return_get_json(usermap_url, self.headers)
        userdict = {u["uid"]: u["name"] for u in users}
        return userdict


class StarFishQuery:
    def __init__(self, headers, api_url, query, group_by, volpath, sec=3):
        self.api_url = api_url
        self.headers = headers
        self.query_id = self.post_async_query(query, group_by, volpath)
        self.result = self.return_results_once_prepared(sec=sec)

    @record_process
    def post_async_query(self, query, group_by, volpath):
        query_url = self.api_url + "async/query/"

        params = {
            "volumes_and_paths": volpath,
            "queries": query,
            "format": "parent_path fn type size blck ct mt at uid gid mode",
            "sort_by": group_by,
            "group_by": group_by,
            "limit": "100000",
            "force_tag_inherit": "false",
            "output_format": "json",
            "delimiter": ",",
            "escape_paths": "false",
            "print_headers": "true",
            "size_unit": "B",
            "humanize_nested": "false",
            "mount_agent": "None",
        }
        r = requests.post(query_url, params=params, headers=self.headers)
        response = r.json()
        logger.debug(f"response: {response}")
        return response["query_id"]

    @record_process
    def return_results_once_prepared(self, sec=3):
        while True:
            query_check_url = self.api_url + "async/query/" + self.query_id
            response = return_get_json(query_check_url, self.headers)
            if response["is_done"] == True:
                result = self.return_query_result()
                return result
            time.sleep(sec)

    def return_query_result(self):
        query_result_url = self.api_url + "async/query_result/" + self.query_id
        response = return_get_json(query_result_url, self.headers)
        return response


class ColdFrontDB:

    @record_process
    def produce_lab_dict(self, vol):
        """Create dict of labs to collect and the volumes/tiers associated with them.
        Parameters
        ----------
        vol : string
            If not None, collect only allocations on the specified volume

        Returns
        -------
        labs_resources: dict
            Structured as follows:
            "lab_name": [("volume", "tier"),("volume", "tier")]
        """
        pr_objs = Allocation.objects.only("id", "project")
        pr_dict = {}
        for alloc in pr_objs:
            proj_name = alloc.project.title
            resource_list = alloc.get_resources_as_string.split(', ')
            if proj_name not in pr_dict:
                pr_dict[proj_name] = resource_list
            else:
                pr_dict[proj_name].extend(resource_list)
        lr = pr_dict if not vol else {p:[i for i in r if vol in i] for p, r in pr_dict.items()}
        labs_resources = {p:[tuple(rs.split("/")) for rs in r] for p, r in lr.items()}
        logger.debug(f"labs_resources:\n{labs_resources}")
        return labs_resources


    def check_volume_collection(self, lr, homepath="./coldfront/plugins/sftocf/data/"):
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
        logger.debug(f"labs_resources:{labs_resources}")

        yesterdaystr = (datetime.today()-timedelta(1)).strftime("%Y%m%d")
        dates = [yesterdaystr, datestr]

        for lr_pair in labs_resources:
            lab = lr_pair[0]
            resource = lr_pair[1]
            tier = lr_pair[2]
            fpaths = [f"{homepath}{lab}_{resource}_{n}.json" for n in dates]
            if any(Path(fpath).exists() for fpath in fpaths):
                for fpath in fpaths:
                    if Path(fpath).exists():
                        filepaths.append(fpath)
            else:
                to_collect.append((lab, resource, tier, fpaths[-1],))

        return filepaths, to_collect


    def pull_sf(self, volume=None):
        """Query Starfish to produce json files of lab usage data.
        Return a set of produced filepaths.
        """
        # 1. produce dict of all labs to be collected and the volumes on which their data is located
        lr = self.produce_lab_dict(volume)
        # 2. produce list of files that have been collected and list of lab/volume/filename tuples to collect
        filepaths, to_collect = self.check_volume_collection(lr)
        # 3. produce set of all volumes to be queried
        vol_set = {i[1] for i in to_collect}
        servers_vols = [(k, vol) for k, v in svp.items() for vol in vol_set if vol in v.keys()]
        for server_vol in servers_vols:
            s = server_vol[0]
            vol = server_vol[1]
            paths = svp[s][vol]
            to_collect_subset = [t for t in to_collect if t[1] == vol]
            logger.debug(f"vol:{vol}\nto_collect_subset:{to_collect_subset}")
            server = StarFishServer(s)
            fpaths = collect_starfish_usage(server, vol, paths, to_collect_subset)
            filepaths.extend(fpaths)
        return set(filepaths)


    def push_cf(self, filepaths, clean):
        for f in filepaths:
            errors = False
            content = read_json(f)
            usernames = [d['username'] for d in content['contents']]
            resource = content['volume'] + "/" + content['tier']

            user_models = get_user_model().objects.only("id","username")\
                    .filter(username__in=usernames)
            log_missing_user_models(content["project"], user_models, usernames)

            project = Project.objects.get(title=content["project"])
            # find project allocation
            try:
                allocation = Allocation.objects.get(project=project, resources__name=resource)
            except Allocation.MultipleObjectsReturned:
                logger.debug(f"Too many allocations for project id {project.id}; choosing one with 'Allocation Information' in justification.")
                # try:
                allocation = Allocation.objects.get(
                    project=project,
                    resources__name=resource,
                    justification__icontains='Allocation Information',
                    justification__endswith=project.title)
                # except Allocation.MultipleObjectsReturned:
                #     logger.warning("Too many allocations for project id {project.id}, matching justifications; choosing the first. Fix this duplication.")
                #     allocations = Allocation.objects.filter(
                #         project_id=project.id,
                #         justification__icontains='Allocation Information',
                #         justification__endswith=project.title)
                #     for a in allocations:
                #         logger.warning(f"Duplicate item:{a}")
                #     allocation = allocations.first()
            logger.debug(f"{project.title}\n usernames: {usernames}\n user_models: {[u.username for u in user_models]}")

            for user in user_models:
                userdict = [d for d in content['contents'] if d["username"] == user.username][0]
                model = user_models.get(username=userdict["username"])
                try:
                    self.update_usage(model, userdict, allocation)
                except Exception as e:
                    logger.warning("EXCEPTION FOR ENTRY: {}".format(e), exc_info=True)
                    errors = True
            if not errors and clean:
                os.remove(f)
        logger.debug("push_cf complete")


    def update_usage(self, user, userdict, allocation):
        usage, unit = split_num_string(userdict["size_sum_hum"])
        logger.debug(f"entering for user:{user.username}")
        try:
            allocationuser = AllocationUser.objects.get(
                allocation=allocation, user=user
            )
        except AllocationUser.DoesNotExist:
            logger.info("creating allocation user:")
            AllocationUser.objects.create(
                allocation=allocation,
                created=timezone.now(),
                status=AllocationUserStatusChoice.objects.get(name='Active'),
                user=user
            )
            allocationuser = AllocationUser.objects.get(
                allocation=allocation, user=user
            )

        allocationuser.usage_bytes = userdict["size_sum"]
        allocationuser.usage = usage
        allocationuser.unit = unit
        # automatically updates "modified" field & adds old record to history
        allocationuser.save()
        logger.debug(f"successful entry: {userdict['groupname']}, {userdict['username']}")



def clean_data_dir(homepath):
    """Remove json from data folder that's more than a week old
    """
    files = os.listdir(homepath)
    json_files = [f for f in files if ".json" in f]
    now = time.time()
    for f in json_files:
        fpath = f"{homepath}{f}"
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
    n = re.search(r"\d*\.?\d+", x).group()
    s = x.replace(n, "")
    return n, s

def return_get_json(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()

def save_json(file, contents):
    with open(file, "w") as fp:
        json.dump(contents, fp, sort_keys=True, indent=4)

def read_json(filepath):
    logger.debug(f"read_json for {filepath}")
    with open(filepath, "r") as json_file:
        data = json.loads(json_file.read())
    return data

def locate_or_create_dirpath(dpath):
    if not os.path.exists(dpath):
        os.makedirs(dpath)
        logger.info(f"created new directory {dpath}")

@record_process
def collect_starfish_usage(server, volume, volumepath, projects):
    """
    Parameters
    ----------
    server : object
    volume : string
    volumepath : list of strings
    projects : list of tuples

    Returns
    -------
    filepaths : list of strings
    """
    filepaths = []
    datestr = datetime.today().strftime("%Y%m%d")
    locate_or_create_dirpath("./coldfront/plugins/sftocf/data/")
    logger.debug(f"projects: {projects}")
    for t in projects:
        p = t[0]
        tier = t[2]
        filepath = t[3]
        lab_volpath = volumepath[1] if "_l3" in p else volumepath[0]
        logger.debug(f"filepath: {filepath} lab: {p} volpath: {lab_volpath}")
        usage_query = server.create_query(
            f"type=f groupname={p}", "username, groupname", f"{volume}:{lab_volpath}"
        )
        data = usage_query.result
        logger.debug("usage_query.result:{}".format(data))
        if not data:
            logger.warning("No starfish result for lab {}".format(p))
        elif type(data) is dict and "error" in data:
            logger.warning("Error in starfish result for lab {}:\n{}".format(p, data))
        else:
            data = usage_query.result
            logger.debug(data)
            record = {
                "server": server.name,
                "volume": volume,
                "path": lab_volpath,
                "project": p,
                "tier": tier,
                "date": datestr,
                "contents": data,
            }
            save_json(filepath, record)
            filepaths.append(filepath)
    return filepaths


def log_missing_user_models(groupname, user_models, usernames):
    """Identify and record any usernames that lack a matching user_models entry.
    """
    missing_unames = [u for u in usernames if u not in [m.username for m in user_models]]
    if missing_unames:
        fpath = './coldfront/plugins/sftocf/data/missing_ifxusers.csv'
        patterns = [f"{groupname},{uname},{datestr}" for uname in missing_unames]
        write_update_file_line(fpath, patterns)
        logger.warning(f"no IfxUser found for users: {missing_unames}")


def use_zone(project_name):
    # attribute type ID will need to change to match the zone flag.
    try:
        allocation = Allocation.objects.get(justification__contains=project_name)
    except Allocation.MultipleObjectsReturned:
        logger.debug(f"Too many allocations for project {project_name}; narrowing to the one that ends with project name")
        allocation = Allocation.objects.get(
            justification__endswith=project_name)
        logger.debug(f"EXCEPT a_id:{allocation.id}")
    except Allocation.DoesNotExist:
        return False
    if allocation:
        aa_entries = AllocationAttribute.objects.filter(allocation=allocation.id)
        for aa in aa_entries:
            if int(aa.allocation_attribute_type_id) == 747 and aa.value == "True":
                return True
    return False


def generate_headers(token):
    """Generate "headers" attribute by using the "token" attribute.
    """
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer {}".format(token),
    }
    return headers
