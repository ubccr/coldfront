import json
import logging
import os
import re
import requests
import time
import timeit

from datetime import datetime
from pathlib import Path

# from tqdm import tqdm
# from pynput import keyboard
from django.contrib.auth import get_user_model
from coldfront.core.allocation.models import Allocation, AllocationUser
from coldfront.core.project.models import Project
from coldfront.core.utils.common import import_from_settings


logging.basicConfig(filename="sfc.log", format="%(asctime)s %(message)s", filemode="w")
logger = logging.getLogger("sfc")
logger.setLevel(logging.DEBUG)


class StarFishServer:
    """
    """

    def __init__(self, server):
        self.api_url = f"https://{server}.rc.fas.harvard.edu/api/"
        self.token = self.get_auth_token()
        self.headers = self.generate_headers()
        self.volumes = self.get_volume_names()

    def get_auth_token(self):
        """Obtain a token through the auth endpoint.
        """
        logger.debug("get_auth_token")
        # username = import_from_settings('SFUSER')
        # password = import_from_settings('SFPASS')
        username = os.environ.get('SFUSER')
        password = os.environ.get('SFPASS')
        auth_url = self.api_url + "auth/"
        todo = {"username": username, "password": password}
        response = requests.post(auth_url, json=todo)
        # response.status_code
        response_json = response.json()
        print(response_json)
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

    def locate_uid(self, username):
        user = get_user_model().objects.get(username=username)
        return user.id

    def locate_pid(self, labname):
        project = Project.objects.get(title=labname)
        return project.id

    def locate_aaid(self, pid):
        allocation = Allocation.objects.get(project_id=pid)
        return allocation.id

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


def generate_groupname_list():
    pass


def collect_starfish_json(server, servername, volume, volumepath):
    # generate user and group list, then narrow down to groups that
    # have subdirectories in their directory.
    labs = server.get_vol_group_membership(volume)

    usertable = server.get_vol_user_name_ids(volume)
    dir_query = server.create_query(
        "type=d", "groupname", f"{volume}:{volumepath}", sec=2
    )
    logger.info(f"dir_query.result:\s{dir_query.result}")
    present_labs = [d["groupname"] for d in dir_query.result]
    full_labs = [lab for lab in labs if lab["name"] in present_labs]
    logger.info(f"present_labs:\s{present_labs}")

    # run user/group usage query
    usage_query_by_lab = []
    # t = tqdm(full_labs)
    for lab in full_labs:
        logger.debug(str(lab["name"]))
        queryline = "type=f groupname={}".format(str(lab["name"]))
        usage_query = server.create_query(
            queryline, "username, groupname", f"{volume}:{volumepath}", sec=2
        )
        result = usage_query.result
        logger.debug(result)
        if not result:
            pass
        elif type(result) is dict and "error" in result:
            pass
        else:
            usage_query_by_lab.append(result)
            # A test end
    filecontents = {
        "server": servername,
        "volume": volume,
        "volumepath": volumepath,
        "contents": usage_query_by_lab,
    }
    return filecontents


if __name__ == "__main__":
    servername = "holysfdb01"
    volume = "holylfs04"
    volumepath = "HDD/C/LABS"
    server = StarFishServer(servername)
    # define filepath
    datestr = datetime.today().strftime("%Y%m%d")
    filepath = f"sf_query_{servername}_{datestr}.json"
    # check if file exists; if not, create it.
    if Path(filepath).exists():
        pass
    else:
        filecontents = collect_starfish_json(server, servername, volume, volumepath)
        with open(filepath, "w") as fp:
            json.dump(filecontents, fp, sort_keys=True, indent=4)

    coldfrontdb = ColdFrontDB()
    with open(filepath, "r") as myfile:
        data = myfile.read()
    usage_stats = json.loads(data)
    usage_stats["contents"] = [i for l in usage_stats["contents"] for i in l]
    for statdict in usage_stats["contents"]:
        if (
            statdict["groupname"] != "bicepdata_group"
            and statdict["username"] != "root"
        ):
            logger.debug(statdict)
            try:
                coldfrontdb.update_usage(statdict)
            except Exception as e:
                logger.debug("EXCEPTION FOR LAST ENTRY: {}".format(e))
