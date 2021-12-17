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
from django_q.tasks import async_task
from ifxuser.models import IfxUser, Organization
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta
from ifxbilling.models import Account, BillingRecord, ProductUsage

from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.allocation.models import Allocation, AllocationUser, AllocationUserStatusChoice

logger = logging.getLogger("sftocf")
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler('coldfront/plugins/sftocf/sfc.log', 'w')
logger.addHandler(filehandler)

datestr = datetime.today().strftime("%Y%m%d")

svp = {
"holysfdb01": {
    "holylfs04":"HDD/C/LABS",
    'holylfs05':"C/LABS",
    'holystore01':"C/LABS",
    },
"holysfdb02": {
    "boslfs02":"LABS",
    "bos-isilon":"rc_labs",
    "holy-isilon":"rc_labs",
    "holylfs02":"LABS",
  }
}


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
        self.headers = self.generate_headers()
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

    def generate_headers(self):
        """Generate "headers" attribute by using the "token" attribute.
        """
        headers = {
            "accept": "application/json",
            "Authorization": "Bearer {}".format(self.token),
        }
        return headers

    # 2A. Generate list of volumes to search, along with top-level paths
    @record_process
    def get_volume_names(self):
        """ Generate a list of the volumes available on the server.
        """
        vols_paths = {}
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
    def get_vol_user_membership(self, volume):
        usermap_url = self.api_url + "mapping/user_membership?volume_name=" + volume
        userlist = return_get_json(usermap_url, self.headers)
        return userlist

    @record_process
    def get_vol_user_name_ids(self, volume):
        usermap_url = self.api_url + "mapping/user?volume_name=" + volume
        users = return_get_json(usermap_url, self.headers)
        userdict = {u["uid"]: u["name"] for u in users}
        return userdict

    @record_process
    def get_vol_group_membership(self, volume):
        group_url = self.api_url + "mapping/group_membership?volume_name=" + volume
        grouplist = return_get_json(group_url, self.headers)
        return grouplist


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

    # 4. return query results
    @record_process
    def return_results_once_prepared(self, sec=3):
        while True:
            query_check_url = self.api_url + "async/query/" + self.query_id
            response = return_get_json(query_check_url, self.headers)
            if response["is_done"] == True:
                result = self.return_query_result()
                return result
            else:
                time.sleep(sec)


    def return_query_result(self):
        query_result_url = self.api_url + "async/query_result/" + self.query_id
        response = return_get_json(query_result_url, self.headers)
        return response


class LabUser:
    def __init__(self, username, groupname):
        user_entry = get_user_model().objects.get(username=username)
        lab_entry = Project.objects.get(groupname)

        self.user_id = user_entry.user_id
        self.project_id = o.project_id
    # def __init__(self, userdict):
        # self.count = userdict["count"]
        # self.groupname = userdict["groupname"]
        # self.size_sum = userdict["size_sum"]
        # self.size_sum_hum = userdict["size_sum_hum"]
        # self.username = userdict["username"]


class ColdFrontDB:

    @record_process
    def pull_sf(self, volume=None):
        labs_resources = self.generate_project_resource_dict()
        logger.debug(f"labs_resources 1:\n{labs_resources}")
        lr = labs_resources if not volume else {k:v for k, v in labs_resources.items() if volume in v}
        logger.debug(f"labs_resources 2:\n{lr}")
        vol_set = {v[0] for v in lr.values()}
        logger.debug(f"vol_set: {vol_set}")
        serv_vols = generate_serv_vol_dict(vol_set)
        for s, v in serv_vols.items():
            server = StarFishServer(s)
            for vol, path in v.items():
                vol_labs_resources = {l:r for l, r in lr.items() if r[0] == vol}
                logger.debug(f"vol_labs_resources: {vol_labs_resources}")
                filepaths = collect_starfish_usage(server, vol, path, vol_labs_resources)
        return filepaths

    def push_cf(self, filepaths, clean):
        logger.debug(f"push_cf filepaths: {filepaths}")
        for f in filepaths:
            content = read_json(f)
            statdicts = content['contents']
            errors = False
            for statdict in statdicts:
                try:
                    server_tier = content['server'] + "/" + content['tier']
                    self.update_usage(statdict, server_tier)
                except Exception as e:
                    logger.debug("EXCEPTION FOR ENTRY: {}".format(e),  exc_info=True)
                    errors = True
            if not errors and clean:
                    os.remove(f)
        logger.debug("push_cf complete")

    @record_process
    def generate_project_resource_dict(self):
        """
        Return dict with keys as project names and values as a list where [0] is the volume and [1] is the tier.
        """
        pr_entries = Allocation.objects.only("id", "project_id")
        pr_dict = {
            return_pname(o.project_id):o.get_resources_as_string for o in pr_entries}
        pr_dict = {p:r.split("/") for p, r in pr_dict.items()}
        return pr_dict

    def update_usage(self, userdict, server_tier):
        # get ids needed to locate correct allocationuser entry
        # user = LabUser(userdict["username"], userdict["groupname"])
        try:
            user = get_user_model().objects.get(username=userdict["username"])
        except IfxUser.DoesNotExist:
            filepath = './coldfront/plugins/sftocf/data/missing_ifxusers.csv'
            pattern = "{},{}".format(userdict["username"], datestr)
            write_update_file_line(filepath, pattern)
            raise
        project = Project.objects.get(title=userdict["groupname"])
        try:
            allocation = Allocation.objects.get(project_id=project.id)
        except Allocation.MultipleObjectsReturned:
            logger.debug(f"Too many allocations for project id {project.id}; choosing one with 'Allocation Information' in justification.")
            allocation = Allocation.objects.get(
                project_id=project.id, justification__icontains=f"Allocation Information")
            logger.debug(f"EXCEPT a_id:{allocation.id}")
        try:
            allocationuser = AllocationUser.objects.get(
                allocation_id=str(allocation.id), user_id=str(user.id)
            )
        except AllocationUser.DoesNotExist:
            filepath = './coldfront/plugins/sftocf/data/missing_allocationusers.csv'
            logger.info("creating allocation user:")
            allocationuser_obj, _ = AllocationUser.objects.create(
                allocation=allocation,
                created=timezone.now(),
                status=AllocationUserStatusChoice.objects.get(name='Active'),
                user=user
            )
            allocationuser = AllocationUser.objects.get(
                allocation_id=str(allocation.id), user_id=str(user.id)
            )

        allocationuser.usage_bytes = userdict["size_sum"]
        usage, unit = split_num_string(userdict["size_sum_hum"])
        allocationuser.usage = usage
        allocationuser.unit = unit
        # automatically updates "modified" field & adds old record to history
        allocationuser.save()
        logger.debug(f"successful entry: {userdict['groupname']}, {userdict['username']}")

class LocalData():
    def __init__(self):
        self.homepath = "./coldfront/plugins/sftocf/data/"
        confirm_dirpath_exists(self.homepath)

    @record_process
    def sort_collected_uncollected(self, server_name, projects):
        filepaths = []
        for p in list(projects.keys()):
            yesterdaystr = (datetime.today()-timedelta(1)).strftime("%Y%m%d")
            dates = [yesterdaystr, datestr]
            fpaths = [f"{self.homepath}{p}_{server_name}_{n}.json" for n in dates]
            if any(Path(fpath).exists() for fpath in fpaths):
                for fpath in fpaths:
                    if Path(fpath).exists():
                        filepaths.append(fpath)
                        del projects[p]
            else:
                projects[p].append(fpaths[-1])
        return filepaths, projects


    def clean_data_dir(self):
        """Remove json from data folder that's more than a week old
        """
        files = os.listdir(self.homepath)
        json_files = [f for f in files if ".json" in f]
        now = time.time()
        for f in json_files:
            fpath = f"{self.homepath}{f}"
            created = os.stat(fpath).st_ctime
            if created < now - 7 * 86400:
                os.remove(fpath)

def write_update_file_line(filepath, pattern):
    with open(filepath, 'r+') as f:
        if not any(pattern == line.rstrip('\r\n') for line in f):
            f.write(pattern + '\n')
            # f.write(newline)

def return_pname(pid):
    project = Project.objects.get(id=pid)
    return project.title

def return_djangoobj_val(Obj, matchkey, matchval, returnval):
    obj = Obj.objects.get(matchkey=matchval)
    return obj.returnval

def split_num_string(x):
    n = re.search("\d*\.?\d+", x).group()
    s = x.replace(n, "")
    return n, s

def return_get_json(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()

def save_json(file, contents):
    with open(file, "w") as fp:
        json.dump(contents, fp, sort_keys=True, indent=4)

def read_json(filepath):
    logger.debug("read_json for {}".format(filepath))
    with open(filepath, "r") as myfile:
        data = json.loads(myfile.read())
    return data

def confirm_dirpath_exists(dpath):
    if not os.path.exists(dpath):
        os.makedirs(dpath)
        logger.info(f"created new directory {dpath}")

@record_process
def collect_starfish_usage(server, volume, volumepath, projects):
    """

    Returns
    -------
    filepaths : list
        list of filepath names
    """
    projects_prepped = {p:r for p,r in projects.items() if r[0] == volume}
    logger.debug(f"projects: {projects}\nprojects_prepped: {projects_prepped}")
    localdata = LocalData()
    filepaths, projects_to_collect = localdata.sort_collected_uncollected(server.name, projects_prepped)
    for p, r in projects_to_collect.items():
        filepath = r[2]
        lab_volpath = volumepath# + "/{}".format(p)
        queryline = "type=f groupname={}".format(p)
        usage_query = server.create_query(
            queryline, "username, groupname", f"{volume}:{lab_volpath}", sec=2
        )
        data = usage_query.result
        logger.debug("usage_query.result:{}".format(data))
        if not data:
            logger.warning("No starfish result for lab {}".format(p))
        elif type(data) is dict and "error" in data:
            logger.warning("Error in starfish result for lab {}:\n{}".format(p, data))
        else:
            logger.debug(f"data: {data}")
            record = {
                "server": server.name,
                "volume": volume,
                "path": lab_volpath,
                "tier": r[1],
                "date": datestr,
                "contents": data,
            }
            save_json(filepath, record)
            filepaths.append(filepath)
    return filepaths

def collect_costperuser(ifx_uid, lab_name):
    # to get to BillingRecord from ifx_uid:
    # ifx_uid => ProductUsage.product_user_id
    prod_uses = ProductUsage.objects.filter(product_user_id=ifx_uid)
    pu_ids = [pu.id for pu in prod_uses]
    # ProductUsage.id => BillingRecord.product_usage_id

    # to get to BillingRecord from lab_name:
    # lab_name => nanites_organization.code
    nanites_lab = Organization.objects.get(code=lab_name)
    # nanites_organization.id => Account.organization_id
    account = Account.objects.get(organization_id=nanites_lab.id)
    # Account.id => BillingRecord.account_id
    bill = BillingRecord.objects.get(author_id=ifx_uid, account_id=lab.id)
#     # get from billing record
#     author_id = ifx_uid
#     account_id => lab_name
#
#     product_usage_id links to product_usage table, containing
#
# id
# charge
# description
# year
# month
# created
# updated
# account_id
# product_usage_id
# current_state
# percent
# author_id
# updated_by_id
# rate



def generate_serv_vol_dict(vol_set):
    search_svp = {}
    for s, v in svp.items():
        if any(vi in v.keys() for vi in vol_set):
            search_svp[s] = {}
            for vk, p in v.items():
                if vk in vol_set:
                    search_svp[s][vk] = p
    return search_svp
