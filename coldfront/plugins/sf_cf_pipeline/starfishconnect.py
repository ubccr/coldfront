# write a starfish program that can authenticate and pull data from an external server
import requests
import os
import time
import json
from pynput import keyboard
from datetime import datetime
import logging


logging.basicConfig(filename="sfc.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger=logging.getLogger("sfc")
logger.setLevel(logging.DEBUG)


class Server():
    def __init__(self, server):
        self.api_url = f"https://{server}.rc.fas.harvard.edu/api/"
        self.token = self.get_auth_token()
        self.headers = self.generate_headers()
        self.volumes = self.get_volume_names()

    def get_auth_token(self):
        """Obtain a token through the auth endpoint.
        """
        logger.debug("get_auth_token")
        username = os.environ.get("username")
        password = os.environ.get("password")
        auth_url = self.api_url+"auth/"
        todo = {"username":username,"password":password}
        response = requests.post(auth_url, json=todo)
        # response.status_code
        response_json = response.json()
        token = response_json['token']
        logger.debug(token)
        return token

    def generate_headers(self):
        """Generate "headers" attribute by using the "token" attribute.
        """
        headers = {"accept": "application/json", "Authorization": "Bearer {}".format(self.token)}
        return headers

    # 2A. Generate list of volumes to search, along with top-level paths
    def get_volume_names(self):
        """ Generate a list of the volumes available on the server.
        """
        logger.debug("get_volume_names")
        vols_paths = {}
        stor_url = self.api_url+"storage/"
        response = return_get_json(stor_url, self.headers)
        volnames = [i['name'] for i in response['items']]
        return volnames


    # def get_paths(self, volnames):
    #     for name in volnames:
    #         vol_url = stor_url+name
    #         requests = return_get_json(vol_url, self.headers)
    #         pathdicts = requests['items']
    #         vols_paths[name] = [i["Basename"] for i in pathdicts]
    #     logger.debug(paths)
    #     return paths

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
        getsubpaths_url = self.api_url+"storage/"+volpath
        request = return_get_json(getsubpaths_url, self.headers)
        pathdicts = request['items']
        subpaths = [i['Basename'] for i in pathdicts]
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
        query = Query(self.headers, self.api_url, query, group_by, volpath, sec=sec)
        return query

    def get_vol_users(self, volume):
        logger.debug("get_vol_users")
        usermap_url = self.api_url+"mapping/user_membership?volume_name="+volume
        userlist = return_get_json(usermap_url, self.headers)
        return userlist


    # def add_user_ids(self, usagejson):
    #     for userdict in usagejson:
    #         username = userdict['username']


class Query():
    def __init__(self, headers, api_url, query, group_by, volpath, sec=3):
        self.api_url = api_url
        self.headers = headers
        self.query_id = self.post_async_query(query, group_by, volpath)
        self.result = self.return_results_once_prepared(sec=sec)


    def post_async_query(self, query, group_by, volpath):
        logger.debug("post_async_query")
        query_url = self.api_url+"async/query/"

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
            "mount_agent": "None"
        }
        r = requests.post(query_url, params=params, headers=self.headers)
        response = r.json()
        logger.debug(response)
        return response['query_id']


    # 4. return query results
    def return_results_once_prepared(self, sec=3):
        logger.debug("return_results_once_prepared")
        # add a means of triggering query deletion
        while True:
            # delete_query = False
            # with keyboard.Listener(on_press=self.on_press) as listener:
                # while delete_query == False:
            query_check_url = self.api_url+"async/query/"+self.query_id
            response = return_get_json(query_check_url, self.headers)
            if response["is_done"] == True:
                print("query complete!")
                result = self.return_query_result()
                return result
            else:
                print("waiting for query...")
                print(response)
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
        query_result_url = self.api_url+"async/query_result/"+self.query_id
        response = return_get_json(query_result_url, self.headers)
        logger.debug(f"response:\n{response}")
        return response


class User():
    def __init__(self, userdict):
        user.username = userdict['name']
        user.id = userdict['uid']
        user.volume = userdict['volume']
        user.groups = userdict['gids']

    def get_usage(self):
        pass


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


if __name__ == "__main__":
    server = Server("holysfdb02")
    usage_query = server.create_query("type=d",
                            "username, groupname",
                            "holylfs02:LABS", sec=5)
    with open('usage_by_subdir_json.json', 'w') as fp:
        json.dump(usage_query.result, fp, sort_keys=True, indent=4)





    ### Attempt 1 ###
    # lab_query = server.create_query("type=d", "groupname", "holylfs02:LABS")
    # logger.debug(f"lab_query.result:\n{lab_query.result}")
    ## get names of groups to use in paths for user query ##
    # dir_query = server.create_query("type=d", "groupname", "holylfs02:LABS")

    ### Attempt 2 ###
    # subpaths = server.get_subpaths("holylfs02/LABS")
    # usage_by_subdir_json = {}
    ### Attempt 2A ###
    # for sp in subpaths:
    #     logger.debug(f"subpath: {sp}")
    #     path = "holylfs02:LABS/"+sp
    #     user_query = server.create_query("type=f", "username", path)
    #     usage_by_subdir_json[sp] = user_query.result
    ### Attempt 2B ###
    # print(subpaths)
    # allpaths = ["holylfs02:LABS%2F"+sp+"%2F" for sp in subpaths]
    # allpathstring = "/".join(allpaths)
    # user_query = server.create_query("type=f", "username, groupname", allpathstring, sec=5)
    # usage_by_subdir_json["query"] = user_query.result
    #
    # usage_by_subdir_json["datetime"] = str(datetime.utcnow())
    # with open('usage_by_subdir_json.json', 'w') as fp:
    #     json.dump(usage_by_subdir_json, fp, sort_keys=True, indent=4)


    # for user in user_query_result:
    #     username = user['username']
    #     user['fullname'] = get_name(user['username'], lab['groupname'])


    # query_with_user = server.add_user_ids(query_result)
    # users = server.get_vol_users("holylfs02")
