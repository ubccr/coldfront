import os
import re
import csv
import logging
import json
import datetime
import subprocess
from decimal import Decimal
from datetime import date

import ldap.filter
from ldap3 import Connection, Server, MODIFY_ADD, MODIFY_DELETE, Tls
from django.urls import reverse
from django.contrib.auth.models import User

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import email_template_context, send_email_template, build_link
from coldfront.core.allocation.models import (AllocationUserStatusChoice,
                                              AllocationUserRoleChoice,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationAttribute,
                                              AllocationUser,
                                              Allocation)
from coldfront.core.project.models import (ProjectUserStatusChoice,
                                           ProjectUserRoleChoice,
                                           ProjectStatusChoice,
                                           ProjectTypeChoice,
                                           ProjectUser,
                                           Project)
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.plugins.ldap_user_info.utils import LDAPSearch
from coldfront.core.project.utils import (check_if_pi_eligible,
                                          get_new_end_date_from_list,
                                          generate_slurm_account_name,
                                          create_admin_action_for_project_creation)
from coldfront.core.allocation.utils import create_admin_action_for_allocation_creation

logger = logging.getLogger(__name__)

PROJECT_PERMISSIONS_PER_TYPE = import_from_settings('PROJECT_PERMISSIONS_PER_TYPE', False)
ENABLE_LDAP_ELIGIBILITY_SERVER = import_from_settings('ENABLE_LDAP_ELIGIBILITY_SERVER', False)
ENABLE_LDAP_SLATE_PROJECT_SYNCING = import_from_settings('ENABLE_LDAP_SLATE_PROJECT_SYNCING', False)
SLATE_PROJECT_ELIGIBILITY_ACCOUNT = import_from_settings('SLATE_PROJECT_ELIGIBILITY_ACCOUNT', '')
SLATE_PROJECT_ACCOUNT = import_from_settings('SLATE_PROJECT_ACCOUNT', '')
SLATE_PROJECT_DIR = import_from_settings('SLATE_PROJECT_DIR', '')
SLATE_PROJECT_INCOMING_DIR = import_from_settings('SLATE_PROJECT_INCOMING_DIR', '')
SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD = import_from_settings('SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD', 120)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')
if EMAIL_ENABLED:
    SLATE_PROJECT_TICKET_QUEUE = import_from_settings('SLATE_PROJECT_TICKET_QUEUE', '')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')


def send_new_allocation_removal_request_email(allocation_removal_request_obj):
    if EMAIL_ENABLED:
        template_context = email_template_context()
        template_context['requestor'] = allocation_removal_request_obj.requestor
        template_context['project'] = allocation_removal_request_obj.allocation.project
        template_context['pi'] = allocation_removal_request_obj.allocation.project.pi
        template_context['resource'] = allocation_removal_request_obj.allocation.get_parent_resource
        template_context['url'] = build_link(reverse('allocation_removal_requests:allocation-removal-request-list'))
        send_email_template(
            'Allocation Removal Request',
            'slate_project/email/new_allocation_removal_request.txt',
            template_context,
            EMAIL_SENDER,
            [SLATE_PROJECT_TICKET_QUEUE, ],
        )


def send_new_allocation_change_request_email(allocation_change_obj):
    if EMAIL_ENABLED:
        project_obj = allocation_change_obj.allocation.project
        pi_name = project_obj.pi.username
        resource_name = allocation_change_obj.allocation.get_parent_resource
        template_context = email_template_context()
        template_context['pi'] = pi_name
        template_context['resource'] = resource_name
        template_context['url'] = build_link(reverse('allocation-change-list'))
        template_context['project_title'] = project_obj.title
        template_context['project_detail_url'] = build_link(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        template_context['project_id'] = project_obj.pk
        template_context['allocation_attribute_changes'] = allocation_change_obj.allocationattributechangerequest_set.all()
        send_email_template(
            f'New Allocation Change Request: {pi_name} - {resource_name}',
            'slate_project/email/new_allocation_change_request.txt',
            template_context,
            EMAIL_SENDER,
            [SLATE_PROJECT_TICKET_QUEUE, ],
        )


def update_user_status(allocation_user_obj, status):
    allocation_user_obj.status = AllocationUserStatusChoice.objects.get(name=status)
    allocation_user_obj.save()


def check_directory_name_format(slate_project_name):
    return not re.search('^[0-9a-zA-Z_-]+$', slate_project_name) is None


def check_directory_name_duplicates(slate_project_name):
    directory_value = '/N/project/' + slate_project_name
    directory_names = AllocationAttribute.objects.filter(
        allocation_attribute_type__name='Slate Project Directory'
    ).values_list('value', flat=True)
    for directory_name in directory_names:
        if directory_name == directory_value:
            return True

    if not os.path.isfile(os.path.join(SLATE_PROJECT_INCOMING_DIR, 'allocated_quantity.csv')):
        logger.warning('allocated_quantity.csv is missing. Skipping additional directory name checking')
        return False

    with open(os.path.join(SLATE_PROJECT_INCOMING_DIR, 'allocated_quantity.csv'), 'r') as slate_projects:
        csv_reader = csv.reader(slate_projects)
        for line in csv_reader:
            if line[0] == slate_project_name:
                return True

    return False


def add_gid_allocation_attribute(allocation_obj):
    ldap_conn = LDAPModify()

    ldap_group = AllocationAttribute.objects.filter(
        allocation=allocation_obj, allocation_attribute_type__name='LDAP Group'
    )
    if not ldap_group.exists():
        logger.warning(
            f'Failed to create a Slate Project GID allocation attribute after allocation approval. The '
            f'allocation (pk={allocation_obj.pk}) is missing the allocation attribute "LDAP Group"'
        )
        return
    ldap_group = ldap_group[0].value

    gid = ldap_conn.get_attribute('gidNumber', ldap_group, 'cn')
    if not gid:
        logger.warning(
            f'Slate Project allocation (pk={allocation_obj.pk}) with LDAP group {ldap_group} does '
            f'not have a GID. Skipping allocation attribute creation'
        )
        return

    _, created = AllocationAttribute.objects.get_or_create(
        allocation=allocation_obj,
        allocation_attribute_type=AllocationAttributeType.objects.get(name='GID'),
        value=gid
    )
    if created:
        logger.info(
            f'Created a Slate Project GID allocation attribute after allocation approval (pk={allocation_obj.pk})'
        )


def sync_smb_status(allocation_obj, allocation_attribute_type_obj=None, ldap_conn=None):
    gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='GID'
    )
    if not gid_obj.exists():
        logger.error(
            f'Failed to sync smb status in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute "GID"'
        )
        return
    gid = int(gid_obj[0].value)

    if allocation_attribute_type_obj is None:
        allocation_attribute_type_obj = AllocationAttributeType.objects.get(
            name='SMB Enabled', linked_resources__name__exact="Slate Project")

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    smb_enabled = ldap_conn.get_attribute('userPassword', gid)
    if not smb_enabled:
        allocation_attribute_obj = AllocationAttribute.objects.filter(
            allocation=allocation_obj,
            allocation_attribute_type=allocation_attribute_type_obj
        )
        if allocation_attribute_obj.exists():
            allocation_attribute_obj[0].delete()
            logger.info(
                f'The allocation attribute {allocation_attribute_type_obj.name} was deleted in '
                f'Slate Project allocation {allocation_obj.pk}' 
            )
        return

    _, created = AllocationAttribute.objects.get_or_create(
        allocation=allocation_obj,
        allocation_attribute_type=allocation_attribute_type_obj,
        value='Yes'
    )

    if created:
        logger.info(
            f'The allocation attribute {allocation_attribute_type_obj.name} was created in Slate '
            f'Project allocation {allocation_obj.pk}' 
        )


def sync_slate_project_user_statuses(slate_project_user_objs):
    """
    Updates the statuses of Slate Project allocation users.

    :param slate_project_user_objs: Queryset of slate project allocation users
    """
    status_objs = {
        'Active': AllocationUserStatusChoice.objects.get(name='Active'),
        'Invited': AllocationUserStatusChoice.objects.get(name='Invited'),
        'Disabled': AllocationUserStatusChoice.objects.get(name='Disabled'),
        'Retired': AllocationUserStatusChoice.objects.get(name='Retired'),
        'Error': AllocationUserStatusChoice.objects.get(name='Error')
    }
    ldap_search_conn = LDAPImportSearch()
    for slate_project_user_obj in slate_project_user_objs:
        new_status = get_new_user_status(slate_project_user_obj.user.username, ldap_search_conn, False)
        if not new_status == slate_project_user_obj.status.name:
            new_status_obj = status_objs.get(new_status)
            if new_status_obj is None:
                logger.error(f'Status {new_status} object is missing')
                new_status_obj = status_objs.get('Error')
            slate_project_user_obj.status = new_status_obj
            slate_project_user_obj.save()
            if new_status == 'Retired':
                project_obj = slate_project_user_obj.allocation.project
                project_pi_obj = project_obj.projectuser_set.get(user=project_obj.pi)
                if project_pi_obj.enable_notifications:
                    send_access_removed_email(slate_project_user_obj, project_pi_obj.user.email)

            logger.info(
                f'User {slate_project_user_obj.user.username}\'s status in allocation ' 
                f'{slate_project_user_obj.allocation.pk} was changed to {new_status}'
            )


def sync_slate_project_directory_name(allocation_obj, ldap_group):
    """
    Updates the Slate Project directory to match the name of the Slate Project LDAP group.

    :allocation_obj: Allocation the slate project directory name should be updated in
    :ldap_group: The name of the Slate Project LDAP group
    """
    allocation_attribute_type = 'Slate Project Directory'
    slate_project_directory_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not slate_project_directory_obj.exists():
        logger.error(
            f'Failed to sync slate project directory in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    slate_project_directory_obj = slate_project_directory_obj[0]
    ldap_group_split = ldap_group.split('_', 1)
    if len(ldap_group_split) < 2 or ldap_group_split[0] != 'condo':
        logger.error(
            f'Failed to sync slate project directory in a Slate Project allocation. The '
            f'allocation\'s (pk={allocation_obj.pk}) ldap group condo assumption failed.'
        )
        return
    slate_project_directory_obj.value = "/N/project/" + ldap_group_split[1]
    slate_project_directory_obj.save()
    logger.info(
        f'Slate Project allocation {allocation_obj.pk}\'s "{allocation_attribute_type}" attribute '
        f'was updated during sync'
    )


def sync_slate_project_ldap_group(allocation_obj, ldap_conn=None):
    """
    Checks if the Slate Project allocation ldap group still matches what is in LDAP. If not then
    update it. 

    :param ldap_conn: LDAPModify initialized connection
    :param allocation_obj: Allocation object that is checked
    """
    allocation_attribute_type = 'GID'
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to sync ldap group in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)

    if ldap_conn is None:
        ldap_conn = LDAPModify()
    if not ldap_conn.check_attribute_exists('gidNumber', ldap_group_gid):
        logger.error(
            f'LDAP: Slate Project GID for allocation {allocation_obj.pk} does not exist. No LDAP group '
            f'sync was performed'
        )
        return
    
    allocation_ldap_group_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='LDAP Group'
    )
    if not allocation_ldap_group_obj.exists():
        logger.error(
            f'Failed to sync ldap group in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    allocation_ldap_group_obj = allocation_ldap_group_obj[0]
    ldap_group = ldap_conn.get_attribute('cn', ldap_group_gid)
    if ldap_group != allocation_ldap_group_obj.value:
        old_ldap_group = allocation_ldap_group_obj.value
        allocation_ldap_group_obj.value = ldap_group
        allocation_ldap_group_obj.save()
        logger.info(
            f'Slate Project allocation {allocation_obj.pk}\'s "LDAP Group" attribute changed from '
            f'{old_ldap_group} to {ldap_group} during sync'
        )
        sync_slate_project_directory_name(allocation_obj, ldap_group)
    

def sync_slate_project_users(allocation_obj, ldap_conn=None, ldap_search_conn=None):
    """
    Checks if the Slate Project allocation is in sync with the Slate Project group in ldap. If not
    it modifies the slate project allocation to re-sync them.

    :param ldap_conn: LDAPModify initialized connection
    :param allocation_obj: Allocation object that is checked
    """
    if not ENABLE_LDAP_SLATE_PROJECT_SYNCING:
        return

    allocation_attribute_type = 'GID'
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to sync users in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)

    if ldap_conn is None:
        ldap_conn = LDAPModify()
    if ldap_search_conn is None:
        ldap_search_conn = LDAPImportSearch()

    if not ldap_conn.check_attribute_exists('gidNumber', ldap_group_gid):
        logger.error(
            f'LDAP: Slate Project GID for allocation {allocation_obj.pk} does not exist. No Slate Project '
            f'user sync was performed'
        )
        return

    read_write_user_objs = allocation_obj.allocationuser_set.filter(
        role__name='read/write', status__name__in=['Active', 'Invited', 'Disabled', 'Retired']
    )
    read_only_user_objs = allocation_obj.allocationuser_set.filter(
        role__name='read only', status__name__in=['Active', 'Invited', 'Disabled', 'Retired']
    )

    ldap_read_write_usernames = ldap_conn.get_users(ldap_group_gid)
    ldap_read_only_usernames = ldap_conn.get_users(ldap_group_gid + 1)

    duplicate_users = set(ldap_read_only_usernames).intersection(set(ldap_read_write_usernames))
    for duplicate_user in duplicate_users:
        if allocation_obj.project.pi.username == duplicate_user:
            ldap_read_only_usernames.remove(duplicate_user)
            logger.warning(f'Project PI {duplicate_user} exists in both Slate Project LDAP groups '
                           f'(allocation pk={allocation_obj.pk}), placing in read/write')
        else:
            ldap_read_write_usernames.remove(duplicate_user)
            logger.warning(f'User {duplicate_user} exists in both Slate Project LDAP groups '
                           f'(allocation pk={allocation_obj.pk}), placing in read only')

    updated_read_write_usernames = []
    updated_read_only_usernames = []

    for read_write_user_obj in read_write_user_objs:
        username = read_write_user_obj.user.username
        if not username in ldap_read_write_usernames:
            if not username in ldap_read_only_usernames:
                read_write_user_obj.status = AllocationUserStatusChoice.objects.get(name='Removed')
                logger.info(
                    f'User {username} was removed from Slate Project allocation '
                    f'{allocation_obj.pk} during sync'
                )
            else:
                read_write_user_obj.role = AllocationUserRoleChoice.objects.get(name='read only')
                logger.info(
                    f'User {username}\'s role was changed to read only in Slate Project '
                    f'allocation {allocation_obj.pk} during sync'
                )
                updated_read_only_usernames.append(username)
            read_write_user_obj.save()
        else:
            updated_read_write_usernames.append(username)

    for read_only_user_obj in read_only_user_objs:
        username = read_only_user_obj.user.username
        if not username in ldap_read_only_usernames:
            if not username in ldap_read_write_usernames:
                read_only_user_obj.status = AllocationUserStatusChoice.objects.get(name='Removed')
                logger.info(
                    f'User {username} was removed from Slate Project allocation '
                    f'{allocation_obj.pk} during sync'
                )
            else:
                read_only_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                logger.info(
                    f'User {username}\'s role was changed to read/write in Slate Project '
                    f'allocation {allocation_obj.pk} during sync'
                )
                updated_read_write_usernames.append(username)
            read_only_user_obj.save()
        else:
            updated_read_only_usernames.append(username)

    for ldap_read_write_username in ldap_read_write_usernames:
        if ldap_read_write_username not in updated_read_write_usernames:
            user_obj, _ = User.objects.get_or_create(username=ldap_read_write_username)
            project_user_obj = allocation_obj.project.projectuser_set.filter(user=user_obj)
            if not project_user_obj.exists():
                if user_obj.userprofile.title == 'group':
                    ProjectUser.objects.create(
                        project=allocation_obj.project,
                        user=user_obj,
                        status=ProjectUserStatusChoice.objects.get(name='Active'),
                        role=ProjectUserRoleChoice.objects.get(name='Group'),
                        enable_notifications=False
                    )
                else:
                    ProjectUser.objects.create(
                        project=allocation_obj.project,
                        user=user_obj,
                        status=ProjectUserStatusChoice.objects.get(name='Active'),
                        role=ProjectUserRoleChoice.objects.get(name='User')
                    )
                logger.info(
                    f'User {ldap_read_write_username} was added to project '
                    f'{allocation_obj.project.pk} during sync'
                )
            else:
                project_user_obj = project_user_obj[0]
                project_user_obj.status = ProjectUserStatusChoice.objects.get(name='Active')
                project_user_obj.save()

            allocation_user_obj = allocation_obj.allocationuser_set.filter(user=user_obj)
            if not allocation_user_obj.exists():
                AllocationUser.objects.create(
                    allocation=allocation_obj,
                    user=user_obj,
                    status=get_new_user_status(user_obj.username, ldap_search_conn),
                    role=AllocationUserRoleChoice.objects.get(name='read/write')
                )
                logger.info(
                    f'User {ldap_read_write_username} was added to Slate Project allocation '
                    f'{allocation_obj.pk} with role read/write during sync'
                )
            else:
                allocation_user_obj = allocation_user_obj[0]
                old_status = allocation_user_obj.status
                allocation_user_obj.status = get_new_user_status(user_obj.username, ldap_search_conn)
                allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                allocation_user_obj.save()

                if old_status.name != 'Active':
                    logger.info(
                        f'User {ldap_read_write_username} was added to Slate Project allocation '
                        f'{allocation_obj.pk} with role read/write during sync'
                    )
                else:
                    logger.info(
                        f'User {ldap_read_write_username}\'s role was changed to read/write in '
                        f'Slate Project allocation {allocation_obj.pk} during sync'
                    )

    for ldap_read_only_username in ldap_read_only_usernames:
        if ldap_read_only_username not in updated_read_only_usernames:
            user_obj, _ = User.objects.get_or_create(username=ldap_read_only_username)
            project_user_obj = allocation_obj.project.projectuser_set.filter(user=user_obj)
            if not project_user_obj.exists():
                if user_obj.userprofile.title == 'group':
                    ProjectUser.objects.create(
                        project=allocation_obj.project,
                        user=user_obj,
                        status=ProjectUserStatusChoice.objects.get(name='Active'),
                        role=ProjectUserRoleChoice.objects.get(name='Group'),
                        enable_notifications=False
                    )
                else:
                    ProjectUser.objects.create(
                        project=allocation_obj.project,
                        user=user_obj,
                        status=ProjectUserStatusChoice.objects.get(name='Active'),
                        role=ProjectUserRoleChoice.objects.get(name='User')
                    )
                logger.info(
                    f'User {ldap_read_only_username} was added to project '
                    f'{allocation_obj.project.pk} during sync'
                )
            else:
                project_user_obj = project_user_obj[0]
                project_user_obj.status = ProjectUserStatusChoice.objects.get(name='Active')
                project_user_obj.save()

            allocation_user_obj = allocation_obj.allocationuser_set.filter(user=user_obj)
            if not allocation_user_obj.exists():
                AllocationUser.objects.create(
                    allocation=allocation_obj,
                    user=user_obj,
                    status=get_new_user_status(user_obj.username, ldap_search_conn),
                    role=AllocationUserRoleChoice.objects.get(name='read only')
                )
                logger.info(
                    f'User {ldap_read_only_username} was added to Slate Project allocation '
                    f'{allocation_obj.pk} with role read only during sync'
                )
            else:
                allocation_user_obj = allocation_user_obj[0]
                old_status = allocation_user_obj.status
                allocation_user_obj.status = get_new_user_status(user_obj.username, ldap_search_conn)
                allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read only')
                allocation_user_obj.save()

                if old_status.name != 'Active':
                    logger.info(
                        f'User {ldap_read_only_username} was added to Slate Project allocation '
                        f'{allocation_obj.pk} with role read only during sync'
                    )
                else:
                    logger.info(
                        f'User {ldap_read_only_username}\'s role was changed to read only in '
                        f'Slate Project allocation {allocation_obj.pk} during sync'
                    )


def sync_slate_project_allocated_quantity(allocation_obj, ldap_conn=None):
    if ldap_conn == None:
        ldap_conn = LDAPModify()

    allocation_attribute_type = 'GID'
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to sync the allocated quantity in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)

    description = ldap_conn.get_attribute('description', ldap_group_gid)

    if not description:
        logger.warning(f'Slate Project with GID={ldap_group_gid} does not have a description. Skipping allocated quantity sync...')
        return
    
    try:
        quota_split = description.split(',')[-2].split(' ')
        identifier = quota_split[1]
        if not identifier == 'quota':
            logger.warning(
                f'Slate Project with GID={ldap_group_gid} has an improperly formatted description. Skipping allocated quantity sync...')
            return

        allocated_quantity = quota_split[2]
        allocated_quantity = int(allocated_quantity)
    except (IndexError, ValueError):
        logger.warning(
            f'Slate Project with GID={ldap_group_gid} has an improperly formatted description. Skipping allocated quantity sync...')
        return
    
    allocation_attribute_type = 'Allocated Quantity'
    allocated_quantity_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if allocated_quantity_obj is None:
        logger.info(
            f'Slate Project allocation with GID={ldap_group_gid} allocated quantity not found.'
            f'Creating one with value {allocated_quantity}'
        )
        allocated_quantity_obj = AllocationAttribute.objects.create(
            allocation=allocation_obj,
            value=allocated_quantity,
            allocation_attribute_type=allocation_attribute_type
        )
        return

    allocated_quantity_obj = allocated_quantity_obj[0]
    if not int(allocated_quantity_obj.value) == allocated_quantity:
        current_allocated_quantity = allocated_quantity_obj.value
        allocated_quantity_obj.value = allocated_quantity
        allocated_quantity_obj.save()

        logger.info(
            f'Slate Project allocation with GID={ldap_group_gid} allocated quantity was updated'
            f' from {current_allocated_quantity} to {allocated_quantity}'
        )


def sync_slate_project_allocated_quantities():
    logger.info('Syncing Slate Project allocated quantities...')
    allocation_objs = Allocation.objects.filter(
        resources__name='Slate Project', status__name='Active').prefetch_related('allocationattribute_set')
    ldap_conn = LDAPModify()
    for allocation_obj in allocation_objs:
        sync_slate_project_allocated_quantity(allocation_obj, ldap_conn)
    logger.info('Done syncing Slate Project allocated quantities')


def check_slate_project_owner_aginst_current_pi(allocation_obj, ldap_conn=None):
    if ldap_conn == None:
        ldap_conn = LDAPModify()

    pi = allocation_obj.project.pi.username
    gid_obj = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name='GID')

    if not gid_obj.exists():
        logger.warning(f'Slate Project allocation is missing a GID (allocation pk={allocation_obj.pk}). Skipping mismatch check...')
        return
    
    gid = gid_obj[0].value
    description = ldap_conn.get_attribute('description', gid)

    if not description:
        logger.warning(f'Slate Project with GID={gid} does not have a description. Skipping mismatch check...')
        return
    
    owner = description.split(',')[-1].split(' ')[1]

    if owner != pi:
        logger.warning(f'Found mismatch between RT Project PI and Slate Project owner in '
                        f'allocation {allocation_obj.pk}. PI={pi}, owner={owner}')


def get_pi_total_allocated_quantity(pi_username):
    total_allocated_quantity = 0
    with open(os.path.join(SLATE_PROJECT_INCOMING_DIR, 'netid-total-allocation.csv'), 'r') as netid_total_allocation_csv:
        csv_reader = csv.reader(netid_total_allocation_csv)
        for line in csv_reader:
            if line[0] == pi_username:
                total_allocated_quantity = int(line[1])
                break

    return total_allocated_quantity


def check_pi_total_allocated_quantity(pi_username):
    return get_pi_total_allocated_quantity(pi_username) > SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD


def download_files():
    subprocess.run(['/usr/bin/bash', os.path.join(SLATE_PROJECT_INCOMING_DIR, 'get_hpfs_data.sh')])


def send_expiry_email(allocation_obj):
    """
    Sends an email to the Slate Project ticket queue about an expired slate project.

    :param allocation_obj: Expired allocation object    
    """
    if EMAIL_ENABLED:
        url = f'{CENTER_BASE_URL.strip("/")}{reverse("allocation-detail", kwargs={"pk": allocation_obj.pk})}'
        template_context = {
            'pk': allocation_obj.pk,
            'project_title': allocation_obj.project.title,
            'url': url,
            'pi_email': allocation_obj.project.pi.email
        }

        send_email_template(
            f'A Slate Project Allocation Has Expired',
            'slate_project/email/slate_project_expired.txt',
            template_context,
            EMAIL_SENDER,
            [SLATE_PROJECT_EMAIL]
        )


def send_missing_account_email(email_receivers):
    """
    Sends an email about needing to create a Slate Project account.

    :param email_receiver: Email address to send the email to
    """
    if EMAIL_ENABLED:
        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'signature': EMAIL_SIGNATURE,
            'help_email': SLATE_PROJECT_EMAIL
        }

        send_email_template(
            'Please Create A Slate Project Account',
            'slate_project/email/missing_account_email.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            email_receivers
        )


def get_new_user_status(username, ldap_search_conn=None, return_obj=True):
    """
    Grabs an allocation user status choice based on what accounts the user is in.

    :param allocation_user: Username to check
    :param ldap_search_conn: Pre-established ldap connection for searching for the user
    group
    :param return_obj: Whether or not an allocation user status choice object should be return. If
    not the name of the status is returned.
    """
    if ldap_search_conn is None:
        ldap_search_conn = LDAPImportSearch()

    attributes = ldap_search_conn.search_a_user(username, ['memberOf'])
    accounts = attributes.get('memberOf')
    if SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts and SLATE_PROJECT_ACCOUNT in accounts:
        status = 'Active'
    elif SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts and not SLATE_PROJECT_ACCOUNT in accounts:
        status = 'Invited'
    elif not SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts and SLATE_PROJECT_ACCOUNT in accounts:
        status = 'Disabled'
    elif not SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts and not SLATE_PROJECT_ACCOUNT in accounts:
        status = 'Retired'

    if return_obj:
        return AllocationUserStatusChoice.objects.get(name=status)

    return status


def send_access_removed_email(allocation_user, receiver):
    """
    Sends an email to the receiver about a user losing access to their Slate Project.

    :allocation_user: Allocation user who lost access
    :receiver: Email address of who should receive the email
    """
    if EMAIL_ENABLED:
        allocation_obj = allocation_user.allocation
        user = allocation_user.user
        if user.first_name:
            name = f'{user.first_name} {user.last_name}'
        else:
            name = user.username
        template_context = {
            'name': name,
            'project_title': allocation_obj.project.title,
            'center_name': EMAIL_CENTER_NAME,
            'signature': EMAIL_SIGNATURE
        }

        send_email_template(
            f'{name}\'s Slate Project Access Has Been Removed',
            'slate_project/email/access_removed.txt',
            template_context,
            SLATE_PROJECT_EMAIL,
            [receiver]
        )


def check_slate_project_account(project_pi, user_obj, notifications_enabled, ldap_search_conn=None, ldap_eligibility_conn=None):
    """
    Checks if the user is in the eligibility group in LDAP. If they aren't it adds them and sends
    an email to the user about creating a Slate Project account. If they are in it but do not have
    a Slate Project account it will also send the email. Returns True if the user is added to the
    eligibility group, else False.

    :param user_obj: User to check
    :param notifications_enabled: Whether or not the user should receive an email
    :param ldap_search_conn: Pre-established ldap connection for searching for the Slate Project
    group
    :param ldap_eligibility_coon: Pre-established ldap connection for searching for the eligibility
    group
    """
    if ldap_search_conn is None:
        ldap_search_conn = LDAPSearch()
    if ldap_eligibility_conn is None:
        ldap_eligibility_conn = LDAPEligibilityGroup()

    attributes = ldap_search_conn.search_a_user(user_obj.username, ['memberOf'])
    accounts = attributes.get('memberOf')
    if not SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts:
        # Do nothing if they have a slate project account but are not in the eligibility account
        if SLATE_PROJECT_ACCOUNT in accounts:
            return False
        added, output = ldap_eligibility_conn.add_user(user_obj.username)
        if not added:
            logger.error(
                f'LDAP: Failed to add user {user_obj.username} to the HPFS ADS eligibility '
                f'group. Reason: {output}'
            )
        else:
            logger.info(
                f'LDAP: Added user {user_obj.username} to the HPFS ADS eligibility group'
            )
            if notifications_enabled:
                send_missing_account_email([project_pi.email, user_obj.email])
            return True
    elif not SLATE_PROJECT_ACCOUNT in accounts:
        if notifications_enabled:
            send_missing_account_email([project_pi.email, user_obj.email])

    return False


def add_slate_project_groups(allocation_obj):
    """
    Creates a new slate project read/write and read only group and adds all of the active
    allocation users. If the allocation already has a GID then no new groups are created.

    :param allocation_obj: The allocation the groups are being created from
    """
    gid_attribute_type = AllocationAttributeType.objects.filter(
        name='GID', linked_resources__name__exact="Slate Project")
    if not gid_attribute_type.exists():
        logger.error(
            f'Allocation attribute type GID does not exists. No new ldap groups were created.'
        )
        allocation_obj.status = AllocationStatusChoice.objects.get('New')
        allocation_obj.save()
        return

    ldap_conn = LDAPModify()
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='GID'
    )
    if ldap_group_gid_obj.exists():
        logger.error(
            f'LDAP: Slate Project allocation GID for allocation {allocation_obj.pk} already ' 
            f'exists. No new groups were created'
        )
        return

    ldap_group_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='LDAP Group'
    )
    if not ldap_group_obj.exists():
        logger.error(
            f'Failed to create slate project groups. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "LDAP Group"'
        )
        return
    ldap_group = ldap_group_obj[0].value

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

    AllocationAttribute.objects.create(
        allocation_attribute_type=gid_attribute_type[0],
        allocation=allocation_obj,
        value=read_write_gid_number
    )

    project_pi = allocation_obj.project.pi

    read_write_allocation_user_objs = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read/write'
    ).prefetch_related('user')
    read_write_users = [read_write_user.user for read_write_user in read_write_allocation_user_objs]
    read_write_usernames = [read_write_user.username for read_write_user in read_write_users]
    added, output = ldap_conn.add_group(
        ldap_group, allocation_obj.project.pi.username, read_write_usernames, read_write_gid_number
    )
    if not added:
        logger.error(
            f'LDAP: Failed to create slate project group {ldap_group} in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added slate project group {ldap_group} in allocation {allocation_obj.pk}'
        )

        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            ldap_search_conn = LDAPSearch()
            ldap_eligibility_conn = LDAPEligibilityGroup()
            project_user_objs = allocation_obj.project.projectuser_set.filter(
                user__in=read_write_users
            ).prefetch_related('user')
            notifications_enabled = {}
            for project_user_obj in project_user_objs:
                notifications_enabled[project_user_obj.user.username] = project_user_obj.enable_notifications
            for allocation_user_obj in read_write_allocation_user_objs:
                check_slate_project_account(
                    project_pi,
                    allocation_user_obj.user,
                    notifications_enabled.get(allocation_user_obj.user.username),
                    ldap_search_conn,
                    ldap_eligibility_conn
                )
                allocation_user_obj.status = get_new_user_status(
                    allocation_user_obj.user.username, ldap_search_conn
                )
                allocation_user_obj.save()

    read_only_allocation_user_objs = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read only'
    ).prefetch_related('user')
    read_only_users = [read_only_user.user for read_only_user in read_only_allocation_user_objs]
    read_only_usernames = [read_only_user.username for read_only_user in read_only_users]
    ldap_group = f'{ldap_group}-ro'
    added, output = ldap_conn.add_group(
        ldap_group, allocation_obj.project.pi.username, read_only_usernames, read_only_gid_number
    )
    if not added:
        logger.error(
            f'LDAP: Failed to create slate project group {ldap_group} in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added slate project group {ldap_group} in allocation {allocation_obj.pk}'
        )

        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            ldap_search_conn = LDAPSearch()
            ldap_eligibility_conn = LDAPEligibilityGroup()
            project_user_objs = allocation_obj.project.projectuser_set.filter(
                user__in=read_only_users
            ).prefetch_related('user')
            notifications_enabled = {}
            for project_user_obj in project_user_objs:
                notifications_enabled[project_user_obj.user.username] = project_user_obj.enable_notifications
            for allocation_user_obj in read_only_allocation_user_objs:
                check_slate_project_account(
                    project_pi,
                    allocation_user_obj.user,
                    notifications_enabled.get(allocation_user_obj.user.username),
                    ldap_search_conn,
                    ldap_eligibility_conn
                )
                allocation_user_obj.status = get_new_user_status(
                    allocation_user_obj.user.username, ldap_search_conn
                )
                allocation_user_obj.save()

def add_user_to_slate_project_group(allocation_user_obj):
    """
    Adds the allocation user to the slate project group associated with the allocation.

    :param allocation_user_obj: The allocation user
    """
    allocation_attribute_type = 'GID'
    allocation_obj = allocation_user_obj.allocation
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to add user {username} to a ldap group. The allocation (pk={allocation_obj.pk}) '
            f'is missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)

    user_role = allocation_user_obj.role.name
    if user_role == 'read only':
        ldap_group_gid += 1

    project_pi = allocation_obj.project.pi

    ldap_conn = LDAPModify()
    added, output = ldap_conn.add_user(username, ldap_group_gid)
    if not added:
        logger.error(
            f'LDAP: Failed to add user {username} to the slate project group with '
            f'{allocation_attribute_type}={ldap_group_gid} in allocation {allocation_obj.pk}. '
            f'Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added user {username} to the slate project group with '
            f'{allocation_attribute_type}={ldap_group_gid} in allocation {allocation_obj.pk}'
        )
        added_to_eligibility_group = False
        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            notifications_enabled = allocation_user_obj.allocation.project.projectuser_set.get(
                user=allocation_user_obj.user
            ).enable_notifications
            added_to_eligibility_group = check_slate_project_account(
                project_pi, allocation_user_obj.user, notifications_enabled
            )

        # The user's new eligibility account is not propagated fast enough to be picked up in 
        # get_new_user_status so we set the status to Eligible ourselves.
        if added_to_eligibility_group:
            allocation_user_obj.status = AllocationUserStatusChoice.objects.get(name='Invited')
            allocation_user_obj.save()
        else:
            allocation_user_obj.status = get_new_user_status(username)
            allocation_user_obj.save()


def remove_slate_project_groups(allocation_obj):
    """
    Removes a slate project read/write and readonly group.

    :param allocation_obj: The allocation the groups are being removed from
    """
    allocation_attribute_type = 'GID'
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to remove slate project group. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)

    ldap_conn = LDAPModify()
    removed, output = ldap_conn.remove_group(ldap_group_gid)
    if not removed:
        logger.error(
            f'Failed to remove slate project group with {allocation_attribute_type}={ldap_group_gid} '
            f'in allocation {allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'Removed slate project group with {allocation_attribute_type}={ldap_group_gid} in '
            f'allocation {allocation_obj.pk}'
        )

    ldap_group_gid += ldap_group_gid

    ldap_conn = LDAPModify()
    removed, output = ldap_conn.remove_group(ldap_group_gid)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove LDAP group {allocation_attribute_type}={ldap_group_gid} in '
            f'allocation {allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed LDAP group {allocation_attribute_type}={ldap_group_gid} in allocation '
            f'{allocation_obj.pk}'
        )


def remove_user_from_slate_project_group(allocation_user_obj):
    """
    Removes the allocation user from the slate project group associated with the allocation.

    :param allocation_user_obj: The allocation user
    """
    allocation_attribute_type = 'GID'
    allocation_obj = allocation_user_obj.allocation
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to remove user {username} from a slate project group. The allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)
    
    user_role = allocation_user_obj.role.name
    if user_role == 'read only':
        ldap_group_gid += 1

    ldap_conn = LDAPModify()
    removed, output = ldap_conn.remove_user(username, ldap_group_gid)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove user {username} from the slate project group with  '
            f'{allocation_attribute_type}={ldap_group_gid} in allocation {allocation_obj.pk}. '
            f'Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed user {username} from the slate project group with '
            f'{allocation_attribute_type}={ldap_group_gid} in allocation {allocation_obj.pk}'
        )

def change_users_slate_project_groups(allocation_user_obj):
    """
    Modifies the allocation user's role in the slate project groups associated with the allocation.

    :param allocation_user_obj: The allocation user 
    """
    allocation_attribute_type = 'GID'
    allocation_obj = allocation_user_obj.allocation
    ldap_group_gid_obj = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid_obj.exists():
        logger.error(
            f'Failed to update user {username}\'s slate project groups from role change. Allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    ldap_group_gid = int(ldap_group_gid_obj[0].value)
    
    new_role = allocation_user_obj.role.name
    if new_role == 'read/write':
        remove_from_group = ldap_group_gid + 1
        add_to_group = ldap_group_gid
    else:
        remove_from_group = ldap_group_gid
        add_to_group = ldap_group_gid + 1
    username = allocation_user_obj.user.username

    ldap_conn = LDAPModify()
    added, output = ldap_conn.add_user(username, add_to_group)
    if not added:
        logger.error(
            f'LDAP: Failed to add user {username} to the slate project group with '
            f'{allocation_attribute_type}={add_to_group} from role change in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
        return 
    removed, output = ldap_conn.remove_user(username, remove_from_group)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove user {username} from the slate project group with'
            f'{allocation_attribute_type}={add_to_group} from role change in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
        return 
        
    logger.info(
        f'LDAP: Changed user {username}\'s slate project group from one with '
        f'{allocation_attribute_type}={remove_from_group} to {allocation_attribute_type}={add_to_group} '
        f'in allocation {allocation_obj.pk}'
    )


def get_slate_project_info(username):
    """
    Returns a list of dictionaries that contain a slate project's name, user's access, and owner.

    :param username: Username to find slate project info on
    """
    allocation_user_objs = AllocationUser.objects.filter(
        user__username=username,
        status__name__in=['Active', 'Invited', 'Disabled', 'Retired'],
        allocation__status__name__in=['Active', 'Renewal Requested'],
        allocation__resources__name='Slate Project'
    )

    slate_projects = []
    for allocation_user_obj in allocation_user_objs:
        attribute_obj = allocation_user_obj.allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='Slate Project Directory'
        )
        if not attribute_obj.exists():
            continue
        directory = attribute_obj[0]

        attribute_obj = allocation_user_obj.allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='Allocated Quantity'
        )
        allocated_quantity = f'{attribute_obj[0].value} TB' if attribute_obj.exists() else 'N/A'

        slate_projects.append(
            {
                'name': directory.value.split('/')[-1],
                'access': allocation_user_obj.role.name,
                'owner': allocation_user_obj.allocation.project.pi.username,
                'allocated_quantity': allocated_quantity,
                'allocation_url': reverse("allocation-detail", kwargs={"pk": allocation_user_obj.allocation.pk})
            }
        )

    return slate_projects


def get_estimated_storage_cost(allocation_obj):
    allocated_quantity = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='Allocated Quantity'
    )
    if not allocated_quantity.exists():
        return 0
    
    storage_cost = max(0, int(allocated_quantity[0].value) - 15) * Decimal('5.12')
    return storage_cost


def send_ineligible_users_report():
    """
    Finds and adds ineligible users to an email report.
    """
    allocation_user_objs = AllocationUser.objects.filter(
        status__name__in=['Retired', 'Disabled'],
        allocation__resources__name='Slate Project',
        allocation__status__name='Active'
    ).prefetch_related(
        'allocation__allocationattribute_set',
        'allocation__project__projectuser_set',
        'allocation__project__pi',
        'status',
        'user'
    )
    ineligible_users = {}
    for allocation_user_obj in allocation_user_objs:
        attribute_obj = allocation_user_obj.allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='LDAP Group'
        )
        if not attribute_obj.exists():
            ldap_group = None
        else:
            ldap_group = attribute_obj[0].value
        project_user_obj = allocation_user_obj.allocation.project.projectuser_set.filter(user=allocation_user_obj.user)
        if project_user_obj.exists():
            username = allocation_user_obj.user.username
            username_status = username + ' - ' + allocation_user_obj.status.name
            pi_username = allocation_user_obj.allocation.project.pi.username
            if not ineligible_users.get(username_status):
                ineligible_users[username_status] = {}

            if pi_username == username:
                if not ineligible_users[username_status].get('PI'):
                    ineligible_users[username_status]['PI'] = [ldap_group]
                else:
                    ineligible_users[username_status]['PI'].append(ldap_group)
                continue

            role = project_user_obj[0].role.name
            if not ineligible_users[username_status].get(role):
                ineligible_users[username_status][role] = [ldap_group]
            else:
                ineligible_users[username_status][role].append(ldap_group)

    if ineligible_users:
        current_date = date.today().isoformat()
        with open(os.path.join(SLATE_PROJECT_DIR, f'ineligible_users_{current_date}.txt'), 'w') as ineligible_file:
            for user, roles in ineligible_users.items():
                for role, projects in roles.items():
                    for project in projects:
                        ineligible_file.write(f'{user.split(" - ")[0]},{project}\n')
        logger.info('Slate Project ineligible users file created')

        if EMAIL_ENABLED:
            template_context = {
                'ineligible_users': ineligible_users,
                'current_date': current_date,
            }

            send_email_template(
                'Ineligible Users',
                'slate_project/email/ineligibility_report.txt',
                template_context,
                EMAIL_SENDER,
                [SLATE_PROJECT_EMAIL]
            )
            logger.info('Slate Project ineligible users email report sent')


def send_ineligible_pis_report():
    """
    Finds and adds ineligible PIs to an email report.
    """
    allocation_objs = Allocation.objects.filter(
        resources__name='Slate Project',
        status__name='Active'
    ).select_related(
        'project__pi',
    )
    project_pis = set([allocation.project.pi for allocation in allocation_objs])
    allocation_user_objs = AllocationUser.objects.filter(
        status__name__in=['Retired', 'Disabled'],
        allocation__status__name='Active',
        user__in=project_pis
    ).select_related(
        'allocation',
        'user'
    )
    ineligible_pis = {}
    for allocation_user_obj in allocation_user_objs:
        attribute_obj = allocation_user_obj.allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='LDAP Group'
        )
        if not attribute_obj.exists():
            ldap_group = None
        else:
            ldap_group = attribute_obj[0].value
        username_status = allocation_user_obj.user.username + ' - ' + allocation_user_obj.status.name
        if not ineligible_pis.get(username_status):
            ineligible_pis[username_status] = {}

        if not ineligible_pis[username_status].get('PI'):
            ineligible_pis[username_status]['PI'] = [ldap_group]
        else:
            ineligible_pis[username_status]['PI'].append(ldap_group)

    if EMAIL_ENABLED and ineligible_pis:
        template_context = {
            'ineligible_users': ineligible_pis,
            'current_date': date.today().isoformat(),
        }

        send_email_template(
            'Ineligible PIs',
            'slate_project/email/ineligibility_report.txt',
            template_context,
            EMAIL_SENDER,
            [SLATE_PROJECT_EMAIL]
        )
        logger.info('Slate Project ineligible PIs email report sent')


def create_slate_project_data_file():
    allocation_attribute_types = [
        'Allocated Quantity',
        'GID',
        'LDAP Group',
        'Slate Project Directory'
    ]
    allocation_attribute_objs = AllocationAttribute.objects.filter(
        allocation_attribute_type__name__in=allocation_attribute_types,
        allocation__resources__name='Slate Project'
    ).prefetch_related('allocation', 'allocation_attribute_type')

    allocations = {}
    for allocation_attribute_obj in allocation_attribute_objs:
        id = allocation_attribute_obj.allocation.id
        if allocations.get(id) is None:
            allocations[id] = {
                'Allocation Created': allocation_attribute_obj.allocation.created
            }

        allocations[id].update(
            {allocation_attribute_obj.allocation_attribute_type.name: allocation_attribute_obj.value}
        )

    current_date = date.today().isoformat()
    slate_project_filename = f'slate_project_data_{current_date}.csv'
    with open(os.path.join(SLATE_PROJECT_DIR, slate_project_filename), 'w') as slate_project_csv:
        csv_writer = csv.writer(slate_project_csv)
        csv_writer.writerow(['Allocation Created', *allocation_attribute_types])
        for _, allocation_attributes in allocations.items():
            csv_writer.writerow([
                allocation_attributes.get('Allocation Created'),
                allocation_attributes.get('Allocated Quantity'),
                allocation_attributes.get('GID'),
                allocation_attributes.get('LDAP Group'),
                allocation_attributes.get('Slate Project Directory')
            ])

    logger.info('Created a csv with Slate Project data')

    return slate_project_filename


def send_slate_project_data_file(slate_project_filename):
    subprocess.run(['/usr/bin/bash', os.path.join(SLATE_PROJECT_DIR, 'send_hpfs_data.sh', slate_project_filename)])


def get_info(info, line, current_project):
    if f'"{info}"' in line:
        split_line = line.split(':', 1)
        line_info = split_line[1].strip()
        if not info == 'id':
            if not line_info == 'null':
                line_info = line_info[1:-1]
        try:
            line_info = int(line_info)
        except ValueError:
            pass

        current_project[info] = line_info


def create_allocation_attribute(allocation_obj, aa_type, value):
    if value and value != 'null':
        if value == 'true':
            value = 'Yes'
        elif value == 'false':
            value = 'No'

        AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=AllocationAttributeType.objects.get(name=aa_type, linked_resources__name__exact="Slate Project"),
            allocation=allocation_obj,
            value=value
        )


def update_user_profile(user_obj, ldap_conn):
    attributes = ldap_conn.search_a_user(user_obj.username, ['title'])
    title = attributes.get('title')
    if title:
        user_obj.userprofile.title = title[0]
    else:
        user_obj.userprofile.title = ''
    user_obj.userprofile.save()


def import_slate_projects(json_file_name, out_file_name, importing_user, limit=None):
    importing_user_obj = User.objects.get(username=importing_user)
    todays_date = datetime.date.today()
    with open(json_file_name, 'r') as json_file:
        extra_information = json.load(json_file)
    slate_projects = []
    pi_import_project_counts = {}
    with open(out_file_name, 'r') as import_file:
        next(import_file)
        for line in import_file:
            line = line.strip('\n')
            line_split = line.split(',')

            extra_project_information = extra_information.get(line_split[0])
            if extra_project_information is None:
                abstract = f'Slate Project {line_split[0]}'
                project_title = f'Slate Project {line_split[0]}'
                allocated_quantity = None
            else:
                abstract = extra_project_information.get('abstract')
                project_title = extra_project_information.get('project_title')
                allocated_quantity = extra_project_information.get('allocated_quantity')

            slate_project = {
                "namespace_entry": line_split[0],
                "ldap_group": line_split[1],
                "owner_netid": line_split[2],
                "gid_number": line_split[4],
                "read_write_users": line_split[5].split(' '),
                "read_only_users": line_split[6].split(' '),
                "abstract": abstract,
                "project_title": project_title,
                "allocated_quantity": allocated_quantity,
                "start_date": '-'.join([line_split[3][:4], line_split[3][4:6], line_split[3][6:8]]),
                "project_id": None
            }
            try:
                slate_project["project_id"] = line_split[7]
            except IndexError:
                pass
            slate_projects.append(slate_project)

            if not pi_import_project_counts.get(slate_project.get('owner_netid')):
                pi_import_project_counts[slate_project.get('owner_netid')] = 0
            if not slate_project.get('project_id'):
                pi_import_project_counts[slate_project.get('owner_netid')] += 1

    project_end_date = get_new_end_date_from_list(
        [datetime.datetime(datetime.datetime.today().year, 6, 30), ],
        datetime.datetime.today(),
        90
    )
    if limit is not None:
        slate_projects = slate_projects[:limit]

    status_objs = {
        'Active': AllocationUserStatusChoice.objects.get(name='Active'),
        'Invited': AllocationUserStatusChoice.objects.get(name='Invited'),
        'Disabled': AllocationUserStatusChoice.objects.get(name='Disabled'),
        'Retired': AllocationUserStatusChoice.objects.get(name='Retired'),
        'Error': AllocationUserStatusChoice.objects.get(name='Error')
    }
    ldap_conn = LDAPImportSearch()
    logger.info('Importing Slate Projects...')
    imported = 0
    for slate_project in slate_projects:
        existing_gid = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='GID',
            value=slate_project.get('gid_number'),
            allocation__status__name__in= ['Active', 'New', 'Renewal Pending']
        )
        if existing_gid.exists():
            logger.warning(f'Slate Project GID {slate_project.get("gid_number")} already exists in '
                           f'allocation {existing_gid[0].allocation.pk}. Skipping import...')
            print(f'Slate Project {slate_project.get("namespace_entry")} has already been imported: '
                  f'{build_link(reverse("allocation-detail", kwargs={"pk": existing_gid[0].allocation.pk}))}')

            pi_import_project_counts[slate_project.get('owner_netid')] -= 1
            continue
        user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
        if not created:
            update_user_profile(user_obj, ldap_conn)

        owner_status = get_new_user_status(user_obj.username, ldap_conn)
        if owner_status in ['Retired', 'Disabled']:
            logger.warning(f'Slate Project GID {slate_project.get("gid_number")} has a status of '
                           f'{owner_status}. Skipping import...')
            print(f'Slate Project {slate_project.get("namespace_entry")} has NOT been imported: '
                  f'Owner has a status of {owner_status}')
            continue
        
        project_user_role_obj = ProjectUserRoleChoice.objects.get(name='Manager')

        if slate_project.get('project_id'):
            project_obj = Project.objects.get(pk=slate_project.get('project_id'))
            if project_obj.status.name != 'Active':
                logger.warning(f'Project {slate_project.get("project_id")} to add Slate Project, '
                               f'GID={slate_project.get("gid_number")}, to is not active, '
                               f'Skipping import...')
                print(f'Slate Project {slate_project.get("namespace_entry")} has NOT been imported: '
                      f'The RT Project is not active')
                continue

            if project_obj.pi.username != slate_project.get('owner_netid'):
                logger.warning(f'Mismatch between Slate Project owner, GID={slate_project.get("gid_number")}'
                               f', and RT Project PI, project pk={project_obj.pk}. Skipping import...')
                print(f'Slate Project {slate_project.get("namespace_entry")} has NOT been imported: '
                      f'Mismatch between Slate Project owner and RT Project PI')
                continue
        else:
            if check_if_pi_eligible(user_obj):
                project_perms = PROJECT_PERMISSIONS_PER_TYPE.get('Default') | PROJECT_PERMISSIONS_PER_TYPE.get('Research')
                project_max = project_perms.get('allowed_per_pi')
                project_objs = Project.objects.filter(status__name='Active', pi=user_obj, type__name='Research')
                if project_objs.count() + pi_import_project_counts.get(slate_project.get('owner_netid')) > project_max:
                    logger.warning(f'Slate Project\'s, GID={slate_project.get("gid_number")}, owner '
                                f'{user_obj.username} will be above their max allowed projects after '
                                f'the full import. Skipping import...')
                    print(f'Slate Project {slate_project.get("namespace_entry")} has NOT been imported: '
                        f'Owner will be above their max allowed projects after the full import ')
                    continue

                project_obj = Project.objects.create(
                    title=slate_project.get('project_title'),
                    description=slate_project.get('abstract'),
                    pi=user_obj,
                    requestor=user_obj,
                    type=ProjectTypeChoice.objects.get(name='Research'),
                    status=ProjectStatusChoice.objects.get(name='Active'),
                    end_date=project_end_date
                )
                project_obj.slurm_account_name = generate_slurm_account_name(project_obj)
                project_obj.save()
                pi_import_project_counts[slate_project.get('owner_netid')] -= 1
                create_admin_action_for_project_creation(importing_user_obj, project_obj)

            else:
                logger.warning(f'Slate Project\'s, GID={slate_project.get("gid_number")} owner '
                               f'{user_obj.username} has a title of {user_obj.userprofile.title}. '
                               f'Skipping import...')
                print(f'Slate Project {slate_project.get("namespace_entry")} has NOT been imported: '
                      f'Owner has an ineligible title')
                continue

        read_write_users = slate_project.get('read_write_users')
        read_only_users = slate_project.get('read_only_users')
        all_users = read_write_users + read_only_users
        for user in all_users:
            enable_notifications = True
            if not user:
                continue
            user_obj, created = User.objects.get_or_create(username=user)
            if not created:
                update_user_profile(user_obj, ldap_conn)
            user_profile_obj = UserProfile.objects.get(user=user_obj)
            project_user_role_obj = ProjectUserRoleChoice.objects.get(name='User')
            status_obj = ProjectUserStatusChoice.objects.get(name='Active')
            if user_profile_obj.title == 'group':
                project_user_role_obj = ProjectUserRoleChoice.objects.get(name='Group')
                enable_notifications = False

            if user_obj in [project_obj.pi, project_obj.requestor]:
                project_user_role_obj = ProjectUserRoleChoice.objects.get(name='Manager')

            project_user_query = ProjectUser.objects.filter(user=user_obj, project=project_obj)
            if project_user_query.exists():
                project_user = project_user_query[0]
                project_user.status = status_obj
                project_user.save()
            else:
                ProjectUser.objects.get_or_create(
                    user=user_obj,
                    project=project_obj,
                    role=project_user_role_obj,
                    enable_notifications=enable_notifications,
                    status=status_obj
                )

        allocation_start_date = todays_date
        if slate_project.get('start_date'):
            allocation_start_date = slate_project.get('start_date')

        allocation_obj = Allocation.objects.create(
            project=project_obj,
            justification='No additional information needed at this time.',
            status=AllocationStatusChoice.objects.get(name='Active'),
            start_date=allocation_start_date,
            end_date=project_obj.end_date,
            is_changeable=True
        )
        allocation_obj.resources.add(Resource.objects.get(name='Slate Project'))

        if not all_users:
            user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
            new_status = get_new_user_status(user_obj.username, ldap_conn, False)
            new_status_obj = status_objs.get(new_status)
            if new_status_obj is None:
                logger.error(f'Status {new_status} object is missing')
                new_status_obj = status_objs.get('Error')
            allocation_user_obj, created = AllocationUser.objects.get_or_create(
                user=user_obj,
                allocation=allocation_obj,
                status=new_status_obj
            )
            if created:
                allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                allocation_user_obj.save()
        else:
            for user in read_write_users:
                if not user:
                    continue
                user_obj, created = User.objects.get_or_create(username=user)
                new_status = get_new_user_status(user_obj.username, ldap_conn, False)
                new_status_obj = status_objs.get(new_status)
                if new_status_obj is None:
                    logger.error(f'Status {new_status} object is missing')
                    new_status_obj = status_objs.get('Error')
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=new_status_obj
                )

                if created:
                    allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                    allocation_user_obj.save()

            for user in read_only_users:
                if not user:
                    continue
                user_obj, created = User.objects.get_or_create(username=user)
                new_status = get_new_user_status(user_obj.username, ldap_conn, False)
                new_status_obj = status_objs.get(new_status)
                if new_status_obj is None:
                    logger.error(f'Status {new_status} object is missing')
                    new_status_obj = status_objs.get('Error')
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=new_status_obj
                )

                if created:
                    allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read only')
                    allocation_user_obj.save()

        create_allocation_attribute(allocation_obj, 'GID', slate_project.get('gid_number'))
        create_allocation_attribute(allocation_obj, 'LDAP Group', slate_project.get('ldap_group'))
        create_allocation_attribute(
            allocation_obj,
            'Slate Project Directory',
            '/N/project/' + slate_project.get('namespace_entry')
        )
        if slate_project.get('allocated_quantity'):
            create_allocation_attribute(
                allocation_obj, 'Allocated Quantity', slate_project.get('allocated_quantity')
            )

        logger.info(f'Slate Project, GID={slate_project.get("gid_number")}, was successfully '
                    f'imported into allocation {allocation_obj.pk}')
        print(f'Slate Project {slate_project.get("namespace_entry")} has been imported: '
              f'{build_link(reverse("allocation-detail", kwargs={"pk": allocation_obj.pk}))}')
        imported += 1

        create_admin_action_for_allocation_creation(importing_user_obj, allocation_obj)

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'slate_project': slate_project.get('namespace_entry'),
                'slate_project_url': build_link(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})),
                'email_contact': SLATE_PROJECT_EMAIL,
                'signature': EMAIL_SIGNATURE
            }

            send_email_template(
                'Imported Slate Project',
                'slate_project/email/imported_slate_project.txt',
                template_context,
                EMAIL_SENDER,
                [project_obj.pi.email]
            )

    not_imported = len(slate_projects) - imported
    logger.info(f'Done importing Slate Projects, imported: {imported}, not imported: {not_imported}')


class LDAPImportSearch():
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def search_a_user(self, user_search_string, search_attributes_list=None):
        # Add check if debug is true to run this. If debug is not then write an error to log file.
        assert type(search_attributes_list) is list, 'search_attributes_list should be a list'

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': ldap.filter.filter_format("(sAMAccountName=%s)", [user_search_string]),
                            'attributes': search_attributes_list,
                            'size_limit': 1}
        self.conn.search(**searchParameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = dict.fromkeys(search_attributes_list, [])

        return attributes


class LDAPModify:
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_SLATE_PROJECT_SERVER_URI')
        self.LDAP_BASE_DN = import_from_settings('LDAP_SLATE_PROJECT_BASE_DN')
        self.LDAP_BIND_DN = import_from_settings('LDAP_SLATE_PROJECT_BIND_DN')
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_SLATE_PROJECT_BIND_PASSWORD')
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_SLATE_PROJECT_CONNECT_TIMEOUT', 2.5)

        tls = Tls(ciphers='ALL')
        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT, tls=tls)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error(f'LDAPModify: Failed to bind to LDAP server: {self.conn.result}')

    def add_group(self, group_name, owner, users, gid_number):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        attributes = {
            "objectClass": ["posixGroup", "top"],
            "gidNumber": gid_number,
            "cn": group_name,
            "description": f"added on {date.today().strftime('%Y%m%d')}, {owner} owner"
        }
        if users:
            attributes['memberUid'] = users
        added = self.conn.add(dn, attributes=attributes)
        return added, self.conn.result.get("description")

    def remove_group(self, gid_number):
        group_name = self.get_attribute('cn', gid_number)
        if not group_name:
            return False, f"LDAP Group name missing for GID {gid_number}"

        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        removed = self.conn.delete(dn)
        return removed, self.conn.result.get("description")

    def add_user(self, username, gid_number):
        group_name = self.get_attribute('cn', gid_number)
        if not group_name:
            return False, f"LDAP Group name missing for GID {gid_number}"

        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        changes = {
            "memberUid": [(MODIFY_ADD, [username])]
        }
        added = self.conn.modify(dn, changes)
        return added, self.conn.result.get("description")

    def remove_user(self, username, gid_number):
        group_name = self.get_attribute('cn', gid_number)
        if not group_name:
            return False, f"LDAP Group name missing for GID {gid_number}"

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

    def get_users(self, gid_number):
        searchParameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format('(gidNumber=%s)', [str(gid_number)]),
            'attributes': ['memberUid'],
            'size_limit': 1
        }
        self.conn.search(**searchParameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = {'memberUid': []}
            
        return attributes.get('memberUid')

    def get_attribute(self, attribute, filter_value, default_filter='gidNumber'):
        search_parameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format(f'({default_filter}=%s)', [str(filter_value)]),
            'attributes': [attribute],
            'size_limit': 1
        }

        self.conn.search(**search_parameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = {attribute: ['']}

        attribute = attributes.get(attribute)
        if not attribute:
            return ''

        return attribute[0]
    
    def check_attribute_exists(self, attribute, gid_number):
        search_parameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format('(gidNumber=%s)', [str(gid_number)]),
            'attributes': [attribute]
        }
        self.conn.search(**search_parameters)
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
        self.LDAP_ADS_NETID_FORMAT = import_from_settings('LDAP_ADS_NETID_FORMAT')

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error(f'LDAPEligibilityGroup: Failed to bind to LDAP server: {self.conn.result}')

    def add_user(self, username):
        changes = {
            'member': [(MODIFY_ADD, [self.LDAP_ADS_NETID_FORMAT.format(username)])]
        }
        added = self.conn.modify(self.LDAP_BASE_DN, changes)

        return added, self.conn.result.get("description")

    def check_user_exists(self, username):
        searchParameters = {'search_base': self.LDAP_BASE_DN,
            'search_filter': "(member=*)",
            'attributes': ['member'],
            'size_limit': 1
        }
        self.conn.search(**searchParameters)
        members = json.loads(self.conn.entries[0].entry_to_json()).get("attributes").get("member")
        netid = self.LDAP_ADS_NETID_FORMAT.format(username)
        for member in members:
            if netid == member:
                return True
        
        return False
