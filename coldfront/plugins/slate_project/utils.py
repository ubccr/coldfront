import logging
import json
import os
from datetime import date

import ldap.filter
from ldap3 import Connection, Server, MODIFY_ADD, MODIFY_DELETE

from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import (AllocationUserRoleChoice,
                                              AllocationAttributeType,
                                              AllocationAttribute)

logger = logging.getLogger(__name__)

ENABLE_LDAP_ELIGIBILITY_SERVER = import_from_settings('ENABLE_LDAP_ELIGIBILITY_SERVER', False)


def add_slate_project_groups(allocation_obj):
    """
    Creates a new slate project read/write and read only group and adds all of the active
    allocation users.

    :param allocation_obj: The allocation the groups are being created from
    """
    allocation_attribute_type = 'Namespace Entry'
    namespace_entry = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not namespace_entry.exists():
        logger.error(
            f'Failed to create slate project groups. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    namespace_entry = namespace_entry[0].value
    ldap_group = f'condo_{namespace_entry}'

    ldap_conn = LDAPModify()
    group_exists = ldap_conn.check_group_exists(ldap_group)
    if group_exists:
        logger.info(
            f'LDAP: Slate project groups for allocation {allocation_obj.pk} already exist. No new '
            f'groups were created'    
        )
        return

    gid_number = ldap_conn.find_highest_gid()
    if gid_number is None:
        logger.error(
            f'Highest GID number search returned None. Allocation {allocation_obj.pk}\'s slate '
            f'project groups were not created'
        )
        return
    # New gid number for read/write groups must be even and read only groups must be odd
    read_write_gid_number = gid_number + 1
    if not read_write_gid_number % 2 == 0:
        read_write_gid_number += 1
    read_only_gid_number = read_write_gid_number + 1
    gid_attribute_type = AllocationAttributeType.objects.filter(name='GID')
    if not gid_attribute_type.exists():
        logger.warning(
            f'Allocation attribute type {gid_attribute_type[0]} does not exists. GID attribute was '
            f'not created for allocation {allocation_obj.pk}'
        )
    else:
        AllocationAttribute.objects.create(
            allocation_attribute_type=gid_attribute_type[0],
            allocation=allocation_obj,
            value=read_write_gid_number
        )

    read_write_users = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read/write'
    ).values_list('user__username', flat=True)
    added, output = ldap_conn.add_group(
        ldap_group, allocation_obj.project.pi.username, read_write_users, read_write_gid_number
    )
    if not added:
        logger.error(
            f'LDAP: Failed to create slate project group {ldap_group} for allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added slate project group {ldap_group} for allocation {allocation_obj.pk}'
        )

        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            ldap_security_conn = LDAPEligibilityGroup()
            for allocation_user in read_write_users:
                username = allocation_user.user.username
                if not ldap_security_conn.check_user_exists(username):
                    added, output = ldap_security_conn.add_user(username)
                    if not added:
                        logger.error(
                            f'LDAP: Failed to add user {username} to the HPFS ADS eligibility '
                            f'group. Reason: {output}'
                        )
                    else:
                        logger.info(
                            f'LDAP: Added user {username} to the HPFS ADS eligibility group.'
                        )

    read_only_users = allocation_obj.allocationuser_set.filter(
        status_name='Active', role__name='read only'
    ).values_list('user__username', flat=True)
    ldap_group = f'condo_{namespace_entry}-ro'
    read_write_users = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read/write'
    ).values_list('user__username', flat=True)
    added, output = ldap_conn.add_group(
        ldap_group, allocation_obj.project.pi.username, read_only_users, read_only_gid_number
    )
    if not added:
        logger.error(
            f'LDAP: Failed to create slate project group {ldap_group} for allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added slate project group {ldap_group} for allocation {allocation_obj.pk}'
        )

        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            ldap_security_conn = LDAPEligibilityGroup()
            for allocation_user in read_only_users:
                username = allocation_user.user.username
                if not ldap_security_conn.check_user_exists(username):
                    added, output = ldap_security_conn.add_user(username)
                    if not added:
                        logger.error(
                            f'LDAP: Failed to add user {username} to the HPFS ADS eligibility '
                            f'group. Reason: {output}'
                        )
                    else:
                        logger.info(
                            f'LDAP: Added user {username} to the HPFS ADS eligibility group.'
                        )

def add_user_to_slate_project_group(allocation_user_obj):
    """
    Adds the allocation user to the slate project group associated with the allocation. The 
    allocation must be active.

    :param allocation_user_obj: The allocation user
    """
    allocation_attribute_type = 'Namespace Entry'
    allocation_obj = allocation_user_obj.allocation
    namespace_entry = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not namespace_entry.exists():
        logger.error(
            f'Failed to add user {username} to a ldap group. The allocation (pk={allocation_obj.pk}) '
            f'is missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    namespace_entry = namespace_entry[0].value

    user_role = allocation_user_obj.role.name
    if user_role == 'read/write':
        ldap_group = f'condo_{namespace_entry}'
    else:
        ldap_group = f'condo_{namespace_entry}-ro'

    ldap_conn = LDAPModify()
    added, output = ldap_conn.add_user(ldap_group, username)
    if not added:
        logger.error(
            f'LDAP: Failed to add user {username} to slate project group {ldap_group} for '
            f'allocation {allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added user {username} to the slate project group {ldap_group} for allocation '
            f'{allocation_obj.pk}'
        )

    if ENABLE_LDAP_ELIGIBILITY_SERVER:
        ldap_security_conn = LDAPEligibilityGroup()
        if not ldap_security_conn.check_user_exists(username):
            added, output = ldap_security_conn.add_user(username)
            if not added:
                logger.error(
                    f'LDAP: Failed to add user {username} to the HPFS ADS eligibility group. '
                    f'Reason: {output}'
                )
            else:
                logger.info(f'LDAP: Added user {username} to the HPFS ADS eligibility group.')


def remove_slate_project_groups(allocation_obj):
    """
    Removes a slate project read/write and readonly group.

    :param allocation_obj: The allocation the groups are being removed from
    """
    allocation_attribute_type = 'Namespace Entry'
    namespace_entry = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not namespace_entry.exists():
        logger.error(
            f'Failed to remove slate project group. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    namespace_entry = namespace_entry[0].value

    ldap_conn = LDAPModify()
    read_write_group = f'condo_{namespace_entry}'
    removed, output = ldap_conn.remove_group(read_write_group)
    if not removed:
        logger.error(
            f'Failed to remove slate project group {read_write_group} for allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'Removed slate project group {read_write_group} for allocation {allocation_obj.pk}'
        )

    read_only_group = f'condo_{namespace_entry[0].value}-ro'

    ldap_conn = LDAPModify()
    removed, output = ldap_conn.remove_group(read_only_group)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove LDAP group {read_only_group} for allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed LDAP group {read_only_group} for allocation {allocation_obj.pk}'
        )


def remove_user_from_slate_project_group(allocation_user_obj):
    """
    Removes the allocation user from the slate project group associated with the allocation.

    :param allocation_user_obj: The allocation user
    """
    allocation_attribute_type = 'Namespace Entry'
    allocation_obj = allocation_user_obj.allocation
    namespace_entry = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not namespace_entry.exists():
        logger.error(
            f'Failed to remove user {username} from a slate project group. The allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    namespace_entry = namespace_entry[0].value
    
    user_role = allocation_user_obj.role.name
    if user_role == 'read/write':
        ldap_group = f'condo_{namespace_entry}'
    else:
        ldap_group = f'condo_{namespace_entry}-ro'

    ldap_conn = LDAPModify()
    removed, output = ldap_conn.remove_user(ldap_group, username)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove user {username} from the slate project group {ldap_group} '
            f'for allocation {allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed user {username} from the slate project group {ldap_group} for '
            f'allocation {allocation_obj.pk}'
        )

def change_users_slate_project_groups(allocation_user_obj):
    """
    Modifies the allocation user's role in the slate project groups associated with the allocation.

    :param allocation_user_obj: The allocation user 
    """
    allocation_attribute_type = 'Namespace Entry'
    allocation_obj = allocation_user_obj.allocation
    namespace_entry = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not namespace_entry.exists():
        logger.error(
            f'Failed to update user {username}\'s slate project groups from role change. Allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    namespace_entry = namespace_entry[0].value
    
    new_role = allocation_user_obj.role.name
    if new_role == 'read/write':
        remove_from_group = f'condo_{namespace_entry}-ro'
        add_to_group = f'condo_{namespace_entry}'
    else:
        remove_from_group = f'condo_{namespace_entry}'
        add_to_group = f'condo_{namespace_entry}-ro'
    username = allocation_user_obj.user.username

    ldap_conn = LDAPModify()
    added, output = ldap_conn.add_user(add_to_group, username)
    if not added:
        logger.error(
            f'LDAP: Failed to add user {username} to slate project group condo_{add_to_group} '
            f'from role change in allocation {allocation_obj.pk}. Reason: {output}'
        )
        return 
    removed, output = ldap_conn.remove_user(remove_from_group, username)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove user {username} from slate project group condo_{add_to_group} '
            f'from role change in allocation {allocation_obj.pk}. Reason: {output}'
        )
        return 
        
    logger.info(
        f'LDAP: Changed user {username}\'s slate project group from condo_{remove_from_group} to '
        f'condo_{add_to_group}'
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
    return [] # TODO
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


class LDAPModify:
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_SLATE_PROJECT_SERVER_URI')
        self.LDAP_BASE_DN = import_from_settings('LDAP_SLATE_PROJECT_BASE_DN')
        self.LDAP_BIND_DN = import_from_settings('LDAP_SLATE_PROJECT_BIND_DN')
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_SLATE_PROJECT_BIND_PASSWORD')
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_SLATE_PROJECT_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error(f'LDAPModify: Failed to bind to LDAP server: {self.conn.result}')

    def add_group(self, group_name, owner, users, gid_number):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        attributes = {
            "objectClass": ["posixGroup", "top"],
            "gidNumber": gid_number,
            "cn": group_name,
            "memberUid": users,
            "description": f"added on {date.today().strftime('%Y%m%d')}, {owner} owner"
        }
        added = self.conn.add(dn, attributes=attributes)
        return added, self.conn.result.get("description")

    def remove_group(self, group_name):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        removed = self.conn.delete(dn)
        return removed, self.conn.result.get("description")

    def add_user(self, group_name, username):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        changes = {
            "memberUid": [(MODIFY_ADD, [username])]
        }
        added = self.conn.modify(dn, changes)
        return added, self.conn.result.get("description")

    def remove_user(self, group_name, username):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        changes = {
            "memberUid": [(MODIFY_DELETE, [username])]
        }
        removed = self.conn.modify(dn, changes)
        return removed, self.conn.result.get("description")
    
    def find_highest_gid(self):
        searchParameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': "(objectClass=posixGroup)",
            'attributes': ['gidNumber']
        }
        self.conn.search(**searchParameters)
        if self.conn.entries:
            gid_numbers = []
            for entry in self.conn.entries:
                attributes = json.loads(entry.entry_to_json()).get('attributes')
                gid_number = attributes.get('gidNumber')[0]
                if gid_number is not None:
                    gid_numbers.append(gid_number)

            highest_gid_number = max(gid_numbers)
            return highest_gid_number
        
        return None
    
    def check_group_exists(self, group_name):
        searchParameters = {
            'search_base': f'cn={group_name},{self.LDAP_BASE_DN}',
            'search_filter': "(objectClass=posixGroup)",
            'attributes': ['cn']
        }
        self.conn.search(**searchParameters)
        if self.conn.entries:
            return True
        else:
            return False


class LDAPEligibilityGroup:
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_ELIGIBILITY_SERVER_URI')
        self.LDAP_BASE_DN = import_from_settings('LDAP_ELIGIBILITY_BASE_DN')
        self.LDAP_BIND_DN = import_from_settings('LDAP_ELIGIBILITY_BIND_DN')
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_ELIGIBILITY_BIND_PASSWORD')
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_ELIGIBILITY_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error(f'LDAPModify: Failed to bind to LDAP server: {self.conn.result}')

    def add_user(self, username):
        # self.conn.add(self.LDAP_BASE_DN, attributes={'netId': username})
        return True, ''

    def check_user_exists(self, username):
        searchParameters = {'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format(f"(netId={[username]})"),
            'size_limit': 1
        }
        self.conn.search(**searchParameters)
        if self.conn.entries:
            return True
        
        return False
