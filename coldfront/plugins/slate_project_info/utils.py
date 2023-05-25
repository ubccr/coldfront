import logging
import json
import os

import ldap.filter
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server

logger = logging.getLogger(__name__)


def get_slate_project_gid_to_name_mapping():
    """
    This works with multiple slate projects. Returns a dictionary with the key as the slate
    project's gid and value as its name.
    """
    slate_project_gid_to_name_mapping = {}
    with open(os.path.join('slate_projects', 'slate_projects.txt'), 'r') as file_with_gids:
        for line in file_with_gids:
            split_line = line.split(' ')
            split_line = [ element for element in split_line if element ]
            gid = int(split_line[3])
            name = split_line[8][:-1]
            slate_project_gid_to_name_mapping[gid] = name

    return slate_project_gid_to_name_mapping


def get_slate_project_info(slate_groups):
    """
    This works with multiple slate projects. Returns a list of dictionaries that contain a slate
    project's name, user's access, and owner.

    :param slate_groups: List of slate project group info
    """
    if not slate_groups:
        return []

    slate_project_gid_to_name_mapping = get_slate_project_gid_to_name_mapping()

    slate_project_list = []
    for slate_group in slate_groups:
        gid_number = slate_group['gidNumber'][0]
        slate_project_name = slate_project_gid_to_name_mapping.get(gid_number)
        slate_project_name_read_only = slate_project_gid_to_name_mapping.get(gid_number + 1)
        if slate_project_name or slate_project_name_read_only:
            name = slate_project_name
            access = 'read/write'
            if name is None:
                name = slate_project_name_read_only
                access = 'read only'
            owner = slate_group.get('description')[0].split(',')[1].strip().split(' ')[0]

            slate_project_list.append(
                {
                    'name': name,
                    'access': access,
                    'owner': owner
                }
            )

    return slate_project_list


def get_slate_project_group_info_from_ldap(username):
    """
    Grabs all the slate project groups the username is in. Returns a list of dictionaries that
    contain a slate project group's name, description, and gid number.
    """
    server = Server(
        import_from_settings('LDAP_SLATE_PROJECT_SERVER_URI'), use_ssl=True, connect_timeout=1
    )
    conn = Connection(server)
    if not conn.bind():
        logger.error('LDAP Slate Project: Failed to bind to LDAP server: {}'.format(conn.result))
        return []
    
    searchParameters = {
        'search_base': import_from_settings('LDAP_SLATE_PROJECT_USER_SEARCH_BASE'),
        'search_filter': ldap.filter.filter_format("(memberUid=%s)", [username]),
        'attributes': ['cn', 'description', 'gidNumber']
    }
    conn.search(**searchParameters)
    results = []
    if conn.entries:
        for entry in conn.entries:
            results.append(json.loads(entry.entry_to_json()).get('attributes'))

        logger.info(f'Slate project info found for user {username}')
    else:
        logger.info(f'Slate project info not found for user {username}')
        return []

    return results
