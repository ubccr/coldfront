import logging
import json
import datetime
from decimal import Decimal
from datetime import date

import ldap.filter
from ldap3 import Connection, Server, MODIFY_ADD, MODIFY_DELETE
from django.urls import reverse
from django.contrib.auth.models import User

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
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
from coldfront.core.project.utils import get_new_end_date_from_list, generate_slurm_account_name

logger = logging.getLogger(__name__)

ENABLE_LDAP_ELIGIBILITY_SERVER = import_from_settings('ENABLE_LDAP_ELIGIBILITY_SERVER', False)
ENABLE_LDAP_SLATE_PROJECT_SYNCING = import_from_settings('ENABLE_LDAP_SLATE_PROJECT_SYNCING', False)
if ENABLE_LDAP_ELIGIBILITY_SERVER:
    SLATE_PROJECT_ELIGIBILITY_ACCOUNT = import_from_settings('SLATE_PROJECT_ELIGIBILITY_ACCOUNT')
    SLATE_PROJECT_ACCOUNT = import_from_settings('SLATE_PROJECT_ACCOUNT') 
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')
PROJECT_DEFAULT_MAX_MANAGERS = import_from_settings('PROJECT_DEFAULT_MAX_MANAGERS', 3)
if EMAIL_ENABLED:
    SLATE_PROJECT_EMAIL = import_from_settings('SLATE_PROJECT_EMAIL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')


def sync_slate_project_ldap_group(allocation_obj, ldap_conn):
    """
    Checks if the Slate Project allocation ldap group still matches what is in LDAP. If not then
    update it. 

    :param ldap_conn: LDAPModify initialized connection
    :param allocation_obj: Allocation object that is checked
    """
    allocation_attribute_type = 'GID'
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to sync ldap group in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value

    if ldap_conn is None:
        ldap_conn = LDAPModify()
    if not ldap_conn.check_attribute_exists('gidNumber', ldap_group_gid):
        logger.error(
            f'LDAP: Slate Project GID for allocation {allocation_obj.pk} does not exist. No sync '
            f'was performed'
        )
        return
    
    allocation_ldap_group = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='LDAP Group'
    )
    if not allocation_ldap_group.exists():
        logger.error(
            f'Failed to sync ldap group in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    allocation_ldap_group = allocation_ldap_group[0]
    ldap_group = ldap_conn.get_attribute('cn', ldap_group_gid)
    if ldap_group != allocation_ldap_group.value:
        old_ldap_group = allocation_ldap_group.value
        allocation_ldap_group.value = ldap_group
        allocation_ldap_group.save()
        logger.info(
            f'LDAP: Slate Project LDAP group name changed from {old_ldap_group} to {ldap_group}'
        )
    

def sync_slate_project_users(allocation_obj, ldap_conn=None):
    """
    Checks if the Slate Project allocation is in sync with the Slate Project group in ldap. If not
    it modifies the slate project allocation to re-sync them.

    :param ldap_conn: LDAPModify initialized connection
    :param allocation_obj: Allocation object that is checked
    """
    if not ENABLE_LDAP_SLATE_PROJECT_SYNCING:
        return

    allocation_attribute_type = 'GID'
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to sync users in a Slate Project allocation. The allocation '
            f'(pk={allocation_obj.pk}) is missing the allocation attribute '
            f'"{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    read_write_users = allocation_obj.allocationuser_set.filter(
        role__name='read/write', status__name__in=['Active', 'Inactive']
    )
    read_only_users = allocation_obj.allocationuser_set.filter(
        role__name='read only', status__name__in=['Active', 'Inactive']
    )

    ldap_read_write_usernames = ldap_conn.get_attribute('memberUid', ldap_group_gid)
    ldap_read_only_usernames = ldap_conn.get_attribute('memberUid', ldap_group_gid + 1)

    updated_read_write_usernames = []
    updated_read_only_usernames = []

    for read_write_user in read_write_users:
        username = read_write_user.user.username
        if not username in ldap_read_write_usernames:
            if not username in ldap_read_only_usernames:
                read_write_user.status = AllocationUserStatusChoice.objects.get(name='Removed')
                logger.info(
                    f'User {username} was removed from Slate Project allocation '
                    f'{allocation_obj.pk} during sync'
                )
            else:
                read_write_user.role = AllocationUserRoleChoice.objects.get(name='read only')
                logger.info(
                    f'User {username}\'s role was changed to read only in Slate Project '
                    f'allocation {allocation_obj.pk} during sync'
                )
                updated_read_only_usernames.append(username)
            read_write_user.save()
        else:
            updated_read_write_usernames.append(username)

    for read_only_user in read_only_users:
        username = read_only_user.user.username
        if not username in ldap_read_only_usernames:
            if not username in ldap_read_write_usernames:
                read_only_user.status = AllocationUserStatusChoice.objects.get(name='Removed')
                logger.info(
                    f'User {username} was removed from Slate Project allocation '
                    f'{allocation_obj.pk} during sync'
                )
            else:
                read_only_user.role = AllocationUserRoleChoice.objects.get(name='read/write')
                logger.info(
                    f'User {username}\'s role was changed to read/write in Slate Project '
                    f'allocation {allocation_obj.pk} during sync'
                )
                updated_read_write_usernames.append(username)
            read_only_user.save()
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
                    status=AllocationUserStatusChoice.objects.get(name='Active'),
                    role=AllocationUserRoleChoice.objects.get(name='read/write')
                )
                logger.info(
                    f'User {ldap_read_write_username} was added to Slate Project allocation '
                    f'{allocation_obj.pk} with role read/write during sync'
                )
            else:
                allocation_user_obj = allocation_user_obj[0]
                old_status = allocation_user_obj.status
                allocation_user_obj.status = AllocationUserStatusChoice.objects.get(name='Active')
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
                    status=AllocationUserStatusChoice.objects.get(name='Active'),
                    role=AllocationUserRoleChoice.objects.get(name='read only')
                )
                logger.info(
                    f'User {ldap_read_only_username} was added to Slate Project allocation '
                    f'{allocation_obj.pk} with role read only during sync'
                )
            else:
                allocation_user_obj = allocation_user_obj[0]
                old_status = allocation_user_obj.status
                allocation_user_obj.status = AllocationUserStatusChoice.objects.get(name='Active')
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


def send_missing_account_email(email_receiver):
    """
    Sends an email about needing to create a Slate Project account.

    :param email_receiver: Email address to send the email to
    """
    if EMAIL_ENABLED:
        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'url': 'https://access.iu.edu/Accounts/Create',
            'signature': EMAIL_SIGNATURE,
            'help_email': SLATE_PROJECT_EMAIL
        }

        send_email_template(
            'Please Create A Slate Project Account',
            'slate_project/email/missing_account_email.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            [email_receiver]
        )


def check_slate_project_account(user, notifications_enabled, ldap_search_conn=None, ldap_eligibility_conn=None):
    """
    Checks if the user is in the eligibility group in LDAP. If they aren't it adds them and sends
    an email to the user about creating a Slate Project account. If they are in it but do not have
    a Slate Project account it will also send the email.

    :param user: User to check
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

    attributes = ldap_search_conn.search_a_user(user.username, ['memberOf'])
    accounts = attributes.get('memberOf')
    if not SLATE_PROJECT_ELIGIBILITY_ACCOUNT in accounts:
        # Do nothing if they have a slate project account but are not in the eligibility account
        if SLATE_PROJECT_ACCOUNT in accounts:
            return
        added, output = ldap_eligibility_conn.add_user(user.username)
        if not added:
            logger.error(
                f'LDAP: Failed to add user {user.username} to the HPFS ADS eligibility '
                f'group. Reason: {output}'
            )
        else:
            logger.info(
                f'LDAP: Added user {user.username} to the HPFS ADS eligibility group'
            )
            if notifications_enabled:
                send_missing_account_email(user.email)
    elif not SLATE_PROJECT_ACCOUNT in accounts:
        if notifications_enabled:
            send_missing_account_email(user.email)


def add_slate_project_groups(allocation_obj):
    """
    Creates a new slate project read/write and read only group and adds all of the active
    allocation users. If the allocation already has a GID then no new groups are created.

    :param allocation_obj: The allocation the groups are being created from
    """
    gid_attribute_type = AllocationAttributeType.objects.filter(name='GID')
    if not gid_attribute_type.exists():
        logger.error(
            f'Allocation attribute type GID does not exists. No new ldap groups were created.'
        )
        allocation_obj.status = AllocationStatusChoice.objects.get('New')
        allocation_obj.save()
        return

    ldap_conn = LDAPModify()
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='GID'
    )
    if ldap_group_gid.exists():
        logger.error(
            f'LDAP: Slate Project allocation GID for allocation {allocation_obj.pk} already ' 
            f'exists. No new groups were created'
        )
        return

    ldap_group = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name='LDAP Group'
    )
    if not ldap_group.exists():
        logger.error(
            f'Failed to create slate project groups. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "LDAP Group"'
        )
        return
    ldap_group = ldap_group[0].value

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

    read_write_users = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read/write'
    ).prefetch_related('user')
    read_write_users = [read_write_user.user for read_write_user in read_write_users]
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
            project_users = allocation_obj.project.projectuser_set.filter(
                user__in=read_write_users
            ).prefetch_related('user')
            notifications_enabled = {}
            for project_user in project_users:
                notifications_enabled[project_user.user.username] = project_user.enable_notifications
            for allocation_user in read_write_users:
                check_slate_project_account(
                    allocation_user,
                    notifications_enabled.get(allocation_user.username),
                    ldap_search_conn,
                    ldap_eligibility_conn
                )

    read_only_users = allocation_obj.allocationuser_set.filter(
        status__name='Active', role__name='read only'
    ).prefetch_related('user')
    read_only_users = [read_only_user.user for read_only_user in read_only_users]
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
            project_users = allocation_obj.project.projectuser_set.filter(
                user__in=read_only_users
            ).prefetch_related('user')
            notifications_enabled = {}
            for project_user in project_users:
                notifications_enabled[project_user.user.username] = project_user.enable_notifications
            for allocation_user in read_only_users:
                check_slate_project_account(
                    allocation_user,
                    notifications_enabled.get(allocation_user.username),
                    ldap_search_conn,
                    ldap_eligibility_conn
                )

def add_user_to_slate_project_group(allocation_user_obj):
    """
    Adds the allocation user to the slate project group associated with the allocation.

    :param allocation_user_obj: The allocation user
    """
    allocation_attribute_type = 'GID'
    allocation_obj = allocation_user_obj.allocation
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to add user {username} to a ldap group. The allocation (pk={allocation_obj.pk}) '
            f'is missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value

    user_role = allocation_user_obj.role.name
    if user_role == 'read only':
        ldap_group_gid += 1

    ldap_conn = LDAPModify()
    added, output = ldap_conn.add_user(ldap_group_gid, username)
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
        if ENABLE_LDAP_ELIGIBILITY_SERVER:
            notifications_enabled = allocation_user_obj.allocation.project.projectuser_set.get(
                user=allocation_user_obj.user
            ).enable_notifications
            check_slate_project_account(allocation_user_obj.user, notifications_enabled)


def remove_slate_project_groups(allocation_obj):
    """
    Removes a slate project read/write and readonly group.

    :param allocation_obj: The allocation the groups are being removed from
    """
    allocation_attribute_type = 'GID'
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to remove slate project group. The allocation (pk={allocation_obj.pk}) is '
            f'missing the allocation attribute "{allocation_attribute_type}"'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value

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
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    username = allocation_user_obj.user.username
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to remove user {username} from a slate project group. The allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value
    
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
    ldap_group_gid = allocation_obj.allocationattribute_set.filter(
        allocation_attribute_type__name=allocation_attribute_type
    )
    if not ldap_group_gid.exists():
        logger.error(
            f'Failed to update user {username}\'s slate project groups from role change. Allocation '
            f'{allocation_obj.pk} is missing the allocation attribute {allocation_attribute_type}'
        )
        return
    ldap_group_gid = ldap_group_gid[0].value
    
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
        status__name='Active',
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
        owner = allocation_user_obj.allocation.project.pi.username
        # For imported projects that have a project owner who can't be a PI.
        if owner == 'thcrowe' and allocation_user_obj.allocation.project.requestor:
            owner = allocation_user_obj.allocation.project.requestor.username
        slate_projects.append(
            {
                'name': attribute_obj.value.split('/')[-1],
                'access': allocation_user_obj.role.name,
                'owner': allocation_user_obj.allocation.project.pi.username
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


def send_inactive_users_report():
    """
    Finds and adds inactive users to an email report.
    """
    allocation_users = AllocationUser.objects.filter(
        status__name='Inactive',
        allocation__resources__name='Slate Project',
        allocation__status__name='Active'
    ).prefetch_related(
        'allocation__allocationattribute_set',
        'allocation__project__projectuser_set',
        'allocation__project__pi',
        'user'
    )
    inactive_users = {}
    for allocation_user in allocation_users:
        attribute_obj = allocation_user.allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='Slate Project Directory'
        )
        if not attribute_obj.exist():
            directory = None
        else:
            directory = attribute_obj[0].value
        project_user = allocation_user.allocation.project.projectuser_set.filter(user=allocation_user.user)
        if project_user.exists():
            username = allocation_user.user.username
            pi_username = allocation_user.allocation.project.pi.username
            if not inactive_users.get(username):
                inactive_users[username] = {}

            if pi_username == username:
                if not inactive_users[username].get('PI'):
                    inactive_users[username]['PI'] = [directory]
                else:
                    inactive_users[username]['PI'].append(directory)
                continue

            role = project_user[0].role.name
            if not inactive_users[username].get(role):
                inactive_users[username][role] = [directory]
            else:
                inactive_users[username][role].append(directory)

    if EMAIL_ENABLED and inactive_users:
        template_context = {
            'inactive_users': inactive_users,
            'current_date': date.today().isoformat(),
        }

        send_email_template(
            'Inactive Users',
            'slate_project/email/inactive_users.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            [SLATE_PROJECT_EMAIL]
        )
        logger.info('Inactive users email report sent')


def send_ineligible_pi_report():
    allocations = Allocation.objects.filter(
        resources__name='Slate Project',
        status__name='Active'
    ).select_related(
        'project__pi',
    )
    inactive_users = {}
    for allocation in allocations:
        attribute_obj = allocation.allocationattribute_set.filter(
            allocation_attribute_type__name='Slate Project Directory'
        )
        if not attribute_obj.exist():
            directory = None
        else:
            directory = attribute_obj[0].value
        pi = allocation.project.pi
        pi_status = allocation.project.projectuser_set.get(user=pi).status.name
        if pi_status == 'Inactive':
            username = pi.username
            if not inactive_users.get(username):
                inactive_users[username] = {}

            if not inactive_users[username].get('PI'):
                inactive_users[username]['PI'] = [directory]
            else:
                inactive_users[username]['PI'].append(directory)

    if EMAIL_ENABLED and inactive_users:
        template_context = {
            'inactive_users': inactive_users,
            'current_date': date.today().isoformat(),
        }

        send_email_template(
            'Inactive Users',
            'slate_project/email/inactive_users.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            [SLATE_PROJECT_EMAIL]
        )
        logger.info('Ineligible PIs email report sent')


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


def import_slate_projects(limit=None, json_file_name=None, out_file_name=None):
    todays_date = datetime.date.today()
    with open(json_file_name, 'r') as json_file:
        extra_information = json.load(json_file)
    slate_projects = []
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
                start_date = None
            else:
                abstract = extra_project_information.get('abstract')
                project_title = extra_project_information.get('project_title')
                allocated_quantity = extra_project_information.get('allocated_quantity')
                start_date = extra_project_information.get('start_date')

            slate_project = {
                "namespace_entry": line_split[0],
                "ldap_group": line_split[1],
                "owner_netid": line_split[2],
                "gid_number": line_split[3],
                "read_write_users": line_split[4].split(' '),
                "read_only_users": line_split[5].split(' '),
                "abstract": abstract,
                "project_title": project_title,
                "allocated_quantity": allocated_quantity,
                "start_date": start_date
            }
            slate_projects.append(slate_project)

    # Non faculty, staff, and ACNP should be put in their own projects with a HPFS member as the PI.
    hpfs_pi =  User.objects.get(username="thcrowe")
    project_end_date = get_new_end_date_from_list(
        [datetime.datetime(datetime.datetime.today().year, 6, 30), ],
        datetime.datetime.today(),
        90
    )
    if limit is not None:
        slate_projects = slate_projects[:limit]

    ldap_conn = LDAPImportSearch()
    rejected_slate_projects = []
    for slate_project in slate_projects:
        exists = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='GID', value=slate_project.get('gid_number')
        ).exists()
        if exists:
            continue
        user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
        if not created:
            update_user_profile(user_obj, ldap_conn)

        if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
            rejected_slate_projects.append(slate_project.get('namespace_entry'))
            continue
        
        project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')
        if user_obj.userprofile.title in ['Faculty', 'Staff', 'Academic (ACNP)', ]:
            project_obj, _ = Project.objects.get_or_create(
                title=slate_project.get('project_title'),
                description=slate_project.get('abstract'),
                pi=user_obj,
                max_managers=PROJECT_DEFAULT_MAX_MANAGERS,
                requestor=user_obj,
                type=ProjectTypeChoice.objects.get(name='Research'),
                status=ProjectStatusChoice.objects.get(name='Active'),
                end_date=project_end_date
            )

            project_obj.slurm_account_name = generate_slurm_account_name(project_obj)
            project_obj.save()
        else:
            project_obj, _ = Project.objects.get_or_create(
                title=slate_project.get('project_title'),
                description=slate_project.get('abstract'),
                pi=hpfs_pi,
                max_managers=3,
                requestor=user_obj,
                type=ProjectTypeChoice.objects.get(name='Research'),
                status=ProjectStatusChoice.objects.get(name='Active'),
                end_date=project_end_date
            )

            project_obj.slurm_account_name = generate_slurm_account_name(project_obj)
            project_obj.save()

            ProjectUser.objects.get_or_create(
                user=hpfs_pi,
                project=project_obj,
                role=project_user_role,
                status=ProjectUserStatusChoice.objects.get(name='Active')
            )

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
            project_user_role = ProjectUserRoleChoice.objects.get(name='User')
            status = ProjectUserStatusChoice.objects.get(name='Active')
            if user_profile_obj.title == 'group':
                project_user_role = ProjectUserRoleChoice.objects.get(name='Group')
                enable_notifications = False

            if user_obj in [project_obj.pi, project_obj.requestor]:
                project_user_role = ProjectUserRoleChoice.objects.get(name='Manager')

            if not user_profile_obj.title or user_profile_obj.title in ['Former Employee', 'Retired Staff']:
                status = ProjectUserStatusChoice.objects.get(name='Inactive')

            ProjectUser.objects.get_or_create(
                user=user_obj,
                project=project_obj,
                role=project_user_role,
                enable_notifications=enable_notifications,
                status=status
            )

        allocation_start_date = todays_date
        if slate_project.get('start_date'):
            allocation_start_date = slate_project.get('start_date').split('/')
            allocation_start_date = '-'.join(
                [allocation_start_date[2], allocation_start_date[0], allocation_start_date[1]]
            )

        allocation_obj, created = Allocation.objects.get_or_create(
            project=project_obj,
            status=AllocationStatusChoice.objects.get(name='Active'),
            start_date=allocation_start_date,
            end_date=project_end_date,
            is_changeable=True
        )
        if created:
            allocation_obj.resources.add(Resource.objects.get(name='Slate Project'))

        if not all_users:
            user_obj, created = User.objects.get_or_create(username=slate_project.get('owner_netid'))
            status = AllocationUserStatusChoice.objects.get(name='Active')
            if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                status = AllocationUserStatusChoice.objects.get(name='Inactive')
            allocation_user_obj, created = AllocationUser.objects.get_or_create(
                user=user_obj,
                allocation=allocation_obj,
                status=status
            )
            if created:
                allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                allocation_user_obj.save()
        else:
            for user in read_write_users:
                if not user:
                    continue
                user_obj, created = User.objects.get_or_create(username=user)
                status = AllocationUserStatusChoice.objects.get(name='Active')
                if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                    status = AllocationUserStatusChoice.objects.get(name='Inactive')
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=status
                )

                if created:
                    allocation_user_obj.role = AllocationUserRoleChoice.objects.get(name='read/write')
                    allocation_user_obj.save()

            for user in read_only_users:
                if not user:
                    continue
                user_obj, created = User.objects.get_or_create(username=user)
                status = AllocationUserStatusChoice.objects.get(name='Active')
                if not user_obj.userprofile.title or user_obj.userprofile.title in ['Former Employee', 'Retired Staff']:
                    status = AllocationUserStatusChoice.objects.get(name='Inactive')
                allocation_user_obj, created = AllocationUser.objects.get_or_create(
                    user=user_obj,
                    allocation=allocation_obj,
                    status=status
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

    print(f'Slate projects not imported due to ineligible PI: {", ".join(rejected_slate_projects)}')


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
                            'search_filter': ldap.filter.filter_format("(cn=%s)", [user_search_string]),
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

    def get_attribute(self, attribute, gid_number):
        search_parameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format('(gidNumber=%s)', [gid_number]),
            'attributes': [attribute],
            'size_limit': 1
        }

        self.conn.search(**search_parameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = {attribute: []}

        result = attributes.get(attribute)
        if len(result) > 1:
            return result
        return result[0]
    
    def check_attribute_exists(self, attribute, gid_number):
        search_parameters = {
            'search_base': self.LDAP_BASE_DN,
            'search_filter': ldap.filter.filter_format('(gidNumber=%s)', [gid_number]),
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
        added = self.conn.add(self.LDAP_BASE_DN, attributes={'member': self.LDAP_ADS_NETID_FORMAT.format(username)})
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
