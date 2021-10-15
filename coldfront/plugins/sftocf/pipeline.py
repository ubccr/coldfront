import os
import re
import json
import time
import timeit
import logging
import requests
from pathlib import Path
from datetime import datetime

# from tqdm import tqdm
# from pynput import keyboard

from django_q.tasks import async_task
from django.contrib.auth import get_user_model
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import Allocation, AllocationUser

logging.basicConfig(filename="sfc.log", format="%(asctime)s %(message)s", filemode="w")
logger = logging.getLogger("sfc")
logger.setLevel(logging.DEBUG)


class StarFishServer:
    """
    """

    def __init__(self, server):
        self.name = server
        self.api_url = f"https://{server}.rc.fas.harvard.edu/api/"
        self.token = self.get_auth_token()
        self.headers = self.generate_headers()
        self.volumes = self.get_volume_names()

    def get_auth_token(self):
        """Obtain a token through the auth endpoint.
        """
        logger.debug("get_auth_token")
        username = import_from_settings('SFUSER')
        password = import_from_settings('SFPASS')
        auth_url = self.api_url + "auth/"
        todo = {"username": username, "password": password}
        response = requests.post(auth_url, json=todo)
        # response.status_code
        response_json = response.json()
        logger.debug(response_json)
        token = response_json["token"]
        logger.debug(token)
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
    def get_volume_names(self):
        """ Generate a list of the volumes available on the server.
        """
        logger.debug("get_volume_names")
        vols_paths = {}
        stor_url = self.api_url + "storage/"
        response = return_get_json(stor_url, self.headers)
        volnames = [i["name"] for i in response["items"]]
        logger.debug("volnames:{}".format(volnames))
        return volnames

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
        logger.debug("get_subpaths")
        getsubpaths_url = self.api_url + "storage/" + volpath
        request = return_get_json(getsubpaths_url, self.headers)
        pathdicts = request["items"]
        subpaths = [i["Basename"] for i in pathdicts]
        logger.debug(subpaths)
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

    def get_vol_user_membership(self, volume):
        logger.debug("get_vol_user_membership")
        usermap_url = self.api_url + "mapping/user_membership?volume_name=" + volume
        userlist = return_get_json(usermap_url, self.headers)
        logger.debug(f"userlist:\n{userlist}")
        return userlist

    def get_vol_user_name_ids(self, volume):
        logger.debug("get_vol_user_name_ids")
        usermap_url = self.api_url + "mapping/user?volume_name=" + volume
        users = return_get_json(usermap_url, self.headers)
        userdict = {u["uid"]: u["name"] for u in users}
        logger.debug(f"userdict:\n{userdict}")
        return userdict

    def get_vol_group_membership(self, volume):
        logger.debug("get_vol_groups")
        group_url = self.api_url + "mapping/group_membership?volume_name=" + volume
        grouplist = return_get_json(group_url, self.headers)
        logger.debug(f"grouplist:\n{grouplist}")
        return grouplist


class StarFishQuery:
    def __init__(self, headers, api_url, query, group_by, volpath, sec=3):
        self.api_url = api_url
        self.headers = headers
        self.query_id = self.post_async_query(query, group_by, volpath)
        self.result = self.return_results_once_prepared(sec=sec)

    def post_async_query(self, query, group_by, volpath):
        logger.debug("post_async_query")
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
        logger.debug(response)
        return response["query_id"]

    # 4. return query results
    def return_results_once_prepared(self, sec=3):
        logger.debug("return_results_once_prepared")
        # add a means of triggering query deletion
        while True:
            # delete_query = False
            # with keyboard.Listener(on_press=self.on_press) as listener:
            # while delete_query == False:
            query_check_url = self.api_url + "async/query/" + self.query_id
            response = return_get_json(query_check_url, self.headers)
            if response["is_done"] == True:
                result = self.return_query_result()
                return result
            else:
                time.sleep(sec)
                # listener.join()

    # def on_press(self, key):
    #     print (key)
    #     if key == keyboard.Key.end:
    #         print ('end pressed')
    #         delete_query = True
    #         return False

    def return_query_result(self):
        logger.debug("return_query_result")
        query_result_url = self.api_url + "async/query_result/" + self.query_id
        response = return_get_json(query_result_url, self.headers)
        logger.debug(f"response:\n{response}")
        return response


class UsageStat:
    def __init__(self, userdict):
        self.count = userdict["count"]
        self.groupname = userdict["groupname"]
        self.size_sum = userdict["size_sum"]
        self.size_sum_hum = userdict["size_sum_hum"]
        self.username = userdict["username"]


class ColdFrontDB:

    def generate_user_project_list(self):
        logger.debug("generate_user_project_list")
        # projuser = ProjectUser.objects.get(project_id=)
        projusers = ProjectUser.objects.only("project_id", "user_id")
        logger.debug("projusers: {}".format(projusers))
        d = {}
        for o in projusers:
            p = self.return_projectname(o.project_id)
            u = self.return_username(o.user_id)
            if p not in d.keys():
                d[p] = [u]
            else:
                d[p].append(u)
        logger.debug("generate_user_project_list product: {}".format(d))
        return d

    def generate_project_list(self):
        logger.debug("generate_project_list")
        projects = Project.objects.only("title")
        logger.debug("generate_project_list projects:{}".format(projects))
        return projects


    def locate_uid(self, username):
        user = get_user_model().objects.get(username=username)
        return user.id

    def locate_pid(self, labname):
        project = Project.objects.get(title=labname)
        return project.id

    def locate_aaid(self, pid):
        allocation = Allocation.objects.get(project_id=pid)
        return allocation.id

    def return_username(self, uid):
        user = get_user_model().objects.get(id=uid)
        return user.username

    def return_projectname(self, pid):
        project = Project.objects.get(id=pid)
        return project.title

    def update_usage(self, userdict):
        # get ids needed to locate correct allocationuser entry
        user_id = self.locate_uid(userdict["username"])
        project_id = self.locate_pid(userdict["groupname"])
        allocation_id = self.locate_aaid(project_id)

        allocationuser = AllocationUser.objects.get(
            allocation_id=allocation_id, user_id=user_id
        )
        allocationuser.usage_bytes = userdict["size_sum"]
        usage, unit = split_num_string(userdict["size_sum_hum"])
        allocationuser.usage = usage
        allocationuser.unit = unit
        # "modified" field is automatically updated, old record is
        # automatically added to history
        allocationuser.save()


def split_num_string(x):
    n = re.search("\d*\.?\d+", x).group()
    s = x.replace(n, "")
    return n, s


def generate_volpath_strings(volpathdict):
    logger.debug("generate_volpath_strings")
    string_list = []
    for v, p in volpathdict.items():
        p = [f"{v}:{n}" for n in p if ".txt" not in n]
        string_list.extend(p)
    vpstring = "/".join(string_list)
    logger.debug(vpstring)
    return vpstring


def return_get_json(url, headers):
    response = requests.get(url, headers=headers)
    return response.json()

def save_as_json(file, contents):
    with open(file, "w") as fp:
        json.dump(contents, fp, sort_keys=True, indent=4)

def read_json(filepath):
    logger.debug("read_json for {}".format(filepath))
    with open(filepath, "r") as myfile:
        data = myfile.read()
    return data


def collect_starfish_usage(server, volume, volumepath, projects):
    # generate user and group list, then narrow down to groups that
    # have subdirectories in their directory.

    # run user/group usage query
    usage_query_by_lab = []
    # t = tqdm(full_labs)
    datestr = datetime.today().strftime("%Y%m%d")
    for p in projects:
        filepath = f"./coldfront/plugins/sftocf/data/{p}_{server.name}_{datestr}.json"
        if Path(filepath).exists():
            #append file to usage_query_by_lab and delete all items with p from dict
            data = read_json(filepath)
        else:
            logger.debug("{}".format(p))
            lab_volpath = volumepath# + "/{}".format(p)

            queryline = "type=f groupname={}".format(p)
            usage_query = server.create_query(
                queryline, "username, groupname", f"{volume}:{lab_volpath}", sec=2
            )
            logger.debug("usage_query.result:{}".format(usage_query.result))
            data = usage_query.result
            if not data:
                logger.warning("No starfish result for lab {}".format(p))
                data = []
            elif type(data) is dict and "error" in data:
                logger.warning("Error in starfish result for lab {}:\n{}".format(p, data))
                data = []
            else:
                data = usage_query.result
                logger.debug(data)
                filecontents = {
                "server": server.name,
                "volume": volume,
                "volumepath": volumepath,
                "date": datestr,
                "contents": data,
                }
                save_as_json(filepath, filecontents)
        usage_query_by_lab.extend(data)
    return usage_query_by_lab
