import logging
import json
import os

import ldap.filter
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server

from coldfront.core.allocation.models import AllocationUserRoleChoice

logger = logging.getLogger(__name__)


def add_user_to_ldap(allocation_user_obj):
    """
    Adds the allocation user to the group in LDAP associated with the slate project allocation. The
    allocation must be active. If the user already exists and has the same role then nothing is
    done.

    :param allocation_user_pk: ID of the allocation user
    """
    # Check if the user already exists in LDAP and has the same role.
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return
    print('Activate user4')
    username = allocation_user_obj.user.username
    project_title = allocation_user_obj.allocation.project.title
    logger.info(
        f'Adding {username} to group associated with project "{project_title}" in ldap'
    )


def remove_user_from_ldap(allocation_user_obj):
    """
    Removes the allocation user from the group in LDAP associated with the slate project allocation
    in. If the user does not exist then nothing is done.

    :param allocation_user_pk: ID of the allocation user
    """
    # Check the user already exists in LDAP.
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return

    username = allocation_user_obj.user.username
    project_title = allocation_user_obj.allocation.project.title
    logger.info(
        f'Removing {username} from group associated with project "{project_title}" in ldap'
    )

def change_user_role_in_ldap(allocation_user_obj):
    """
    Modifies the allocation user's role in the group in LDAP associated with the slate project
    allocation. The allocation must be active. If the role already matches then nothing is done.

    :param allocation_user_pk: ID of the allocation user 
    """
    # Check if their role in LDAP is different.
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return

    username = allocation_user_obj.user.username
    project_title = allocation_user_obj.allocation.project.title
    logger.info(
        f'Changing the role of {username} in the group associated with project "{project_title}" in ldap'
    )


def get_slate_project_gid_number(username, namespace_entry):
    server = Server(
        import_from_settings('LDAP_SLATE_PROJECT_SERVER_URI'), use_ssl=True, connect_timeout=1
    )
    conn = Connection(server)
    if not conn.bind():
        return []
    
    searchParameters = {
        'search_base': import_from_settings('LDAP_SLATE_PROJECT_USER_SEARCH_BASE'),
        'search_filter': ldap.filter.filter_format(
            "(&(memberUid=%s)(cn=%s))", [username, 'condo_' + namespace_entry]
        ),
        'attributes': ['gidNumber']
    }
    conn.search(**searchParameters)
    results = []
    if conn.entries:
        for entry in conn.entries:
            results.append(json.loads(entry.entry_to_json()).get('attributes'))

    return results


def get_allocation_user_role(username, namespace_entry):
    gid_number = get_slate_project_gid_number(username, namespace_entry)
    role = 'read/write'
    if gid_number % 2:
        role = 'read only'

    return AllocationUserRoleChoice.objects.get(name=role)


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

    slate_projects = []
    for slate_group in slate_groups:
        gid_number = slate_group.get('gidNumber')[0]
        slate_project_name = slate_project_gid_to_name_mapping.get(gid_number)
        slate_project_name_read_only = slate_project_gid_to_name_mapping.get(gid_number - 1)
        if slate_project_name or slate_project_name_read_only:
            name = slate_project_name
            access = 'read/write'
            if name is None:
                name = slate_project_name_read_only
                access = 'read only'
            owner = slate_group.get('description')[0].split(',')[1].strip().split(' ')[0]

            slate_projects.append(
                {
                    'name': name,
                    'access': access,
                    'owner': owner
                }
            )

    return slate_projects


def get_slate_project_group_info_from_ldap(username):
    """
    Grabs all the slate project groups the username is in. Returns a list of dictionaries that
    contain a slate project group's name, description, and gid number.

    :param username: Username to use in LDAP search for slate project groups
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
