import logging
from django.urls import reverse
from ldap3 import Server, Connection, MODIFY_ADD, MODIFY_DELETE

from coldfront.core.allocation.models import AllocationAttribute, AllocationAttributeType
from coldfront.core.utils.mail import build_link, send_email_template, email_template_context
from coldfront.core.utils.common import import_from_settings
from coldfront.core.user.models import UserProfile

logger = logging.getLogger(__name__)


ENABLE_GEODE_PROJECT_LDAP_INTEGRATION = import_from_settings('ENABLE_GEODE_PROJECT_LDAP_INTEGRATION', False)
if ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
    LDAP_GEODE_PROJECT_BASE_DN = import_from_settings('LDAP_GEODE_PROJECT_BASE_DN')
    LDAP_GEODE_ALL_USERS_GROUP = import_from_settings('LDAP_GEODE_ALL_USERS_GROUP')
    LDAP_GEODE_PROJECT_USER_ACCOUNT_TEMPLATE = import_from_settings('LDAP_GEODE_PROJECT_USER_ACCOUNT_TEMPLATE')
    LDAP_GEODE_PROJECT_GROUP_TEMPLATE = import_from_settings('LDAP_GEODE_PROJECT_GROUP_TEMPLATE')
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED')
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    GEODE_PROJECT_EMAIL = import_from_settings('GEODE_PROJECT_EMAIL')

def send_new_allocation_request_email(project_obj):
    allocation_objs = project_obj.allocation_set.filter(resources__name='Geode-Projects', status__name='New')
    for allocation_obj in allocation_objs:
        if EMAIL_ENABLED:
            template_context = email_template_context()
            template_context['pi'] = project_obj.pi.username
            template_context['resource'] = allocation_obj.get_parent_resource
            template_context['url'] = build_link(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
            template_context['project_title'] = project_obj.title
            template_context['project_detail_url'] = build_link(reverse('project-detail', kwargs={'pk': project_obj.pk}))
            template_context['project_id'] = project_obj.pk
            send_email_template(
                f'New Allocation Request: {project_obj.pi.username} - {allocation_obj.get_parent_resource}',
                'email/new_allocation_request.txt',
                template_context,
                EMAIL_SENDER,
                [GEODE_PROJECT_EMAIL, ],
            )


def add_group(allocation_obj, allocation_attribute_type, group, usernames, role, ldap_conn):
    division = UserProfile.objects.get(user=allocation_obj.project.pi).division
    group_name = f'{LDAP_GEODE_PROJECT_GROUP_TEMPLATE}-{division}-{group}-{role}'
    users = [LDAP_GEODE_PROJECT_USER_ACCOUNT_TEMPLATE.format(username) for username in usernames]
    added, output = ldap_conn.add_group(group_name, users)
    if not added:
        logger.error(
            f'LDAP: Failed to create geode-project group {group_name} in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added geode-project group {group_name} in allocation {allocation_obj.pk}'
        )

        allocation_attribute_type_obj = AllocationAttributeType.objects.filter(name=allocation_attribute_type)
        if not allocation_attribute_type_obj.exists():
            logger.error(
                f'Allocation attribute type "{allocation_attribute_type}" does not exist, allocation '
                f'attribute was not created'
            )
        else:
            allocation_attribute_type_obj = allocation_attribute_type_obj[0]
            AllocationAttribute.objects.get_or_create(
                allocation=allocation_obj,
                allocation_attribute_type=allocation_attribute_type_obj,
                value=group_name
            )

        added, output = ldap_conn.add_user(LDAP_GEODE_ALL_USERS_GROUP, f'cn={group_name},{LDAP_GEODE_PROJECT_BASE_DN}')
        if not added:
            logger.error(
                f'LDAP: Failed to add geode-project group {group_name} into {LDAP_GEODE_ALL_USERS_GROUP} '
                f'in allocation {allocation_obj.pk}. Reason: {output}'
            )
        else:
            logger.info(
                f'LDAP: Added geode-project group {group_name} into {LDAP_GEODE_ALL_USERS_GROUP} '
                f'in allocation {allocation_obj.pk}'
            )


def add_groups(allocation_obj, ldap_conn=None):
    if not ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
        return

    group = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name='Department: Group Name')
    if not group.exists:
        logger.error(
            f'Geode-Project allocation {allocation_obj.pk} is missing the allocation attribute '
            f'"Department: Group Name". No new AD groups were added'
        )
        return
    group = group[0].value

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    alloccation_users = allocation_obj.allocationuser_set.filter(status__name='Active').values_list('user', flat=True)

    usernames = allocation_obj.project.projectuser_set.filter(
        role__name='Manager', user__in=alloccation_users).values_list('user__username', flat=True)
    add_group(allocation_obj, 'Storage: Admin Group', group, usernames, 'Admin', ldap_conn)

    usernames = allocation_obj.project.projectuser_set.filter(
        user__in=alloccation_users).exclude(role__name='Manager').values_list('user__username', flat=True)
    add_group(allocation_obj, 'Storage: Users Group', group, usernames, 'Users', ldap_conn)


def remove_group(allocation_obj, allocation_attribute_type, ldap_conn):
    allocation_attribute = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name=allocation_attribute_type)
    if not allocation_attribute.exists:
        logger.error(
            f'Geode-Project allocation {allocation_obj.pk} is missing the allocation attribute '
            f'"{allocation_attribute_type}". No AD groups were removed'
        )
        return
    
    group = allocation_attribute[0].value

    removed, output = ldap_conn.remove_group(group)
    if not removed:
        logger.error(
            f'LDAP: Failed to remove geode-project group {group} in allocation '
            f'{allocation_obj.pk}. Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed geode-project group {group} in allocation {allocation_obj.pk}'
        )
        allocation_attribute.delete()


def remove_groups(allocation_obj, ldap_conn=None):
    if not ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
        return

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    remove_group(allocation_obj, 'Storage: Users Group', ldap_conn)
    remove_group(allocation_obj, 'Storage: Admin Group', ldap_conn)


def add_user(allocation_user_obj, allocation_attribute_type, ldap_conn=None):
    if not ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
        return

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    allocation_obj = allocation_user_obj.allocation
    allocation_attribute = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name=allocation_attribute_type)
    username = allocation_user_obj.user.username
    if not allocation_attribute.exists:
        logger.error(
            f'Geode-Project allocation {allocation_obj.pk} is missing the allocation attribute '
            f'"{allocation_attribute_type}". {username} was not added to any AD groups '
        )
        return

    group = allocation_attribute[0].value
    added, output = ldap_conn.add_user(group, LDAP_GEODE_PROJECT_USER_ACCOUNT_TEMPLATE.format(username))
    if not added:
        logger.error(
            f'LDAP: Failed to add user {username} into {group} in allocation {allocation_obj.pk}. '
            f'Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Added user {username} to {group} in allocation {allocation_obj.pk}'
        )


def remove_user(allocation_user_obj, allocation_attribute_type, ldap_conn=None):
    if not ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
        return

    if ldap_conn is None:
        ldap_conn = LDAPModify()

    allocation_obj = allocation_user_obj.allocation
    allocation_attribute = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__name=allocation_attribute_type)
    username = allocation_user_obj.user.username
    if not allocation_attribute.exists:
        logger.error(
            f'Geode-Project allocation {allocation_obj.pk} is missing the allocation attribute '
            f'"{allocation_attribute_type}". {username} was not remove from any AD groups '
        )
        return

    group = allocation_attribute[0].value
    added, output = ldap_conn.remove_user(group, LDAP_GEODE_PROJECT_USER_ACCOUNT_TEMPLATE.format(username))
    if not added:
        logger.error(
            f'LDAP: Failed to remove user {username} from {group} in allocation {allocation_obj.pk}. '
            f'Reason: {output}'
        )
    else:
        logger.info(
            f'LDAP: Removed user {username} from {group} in allocation {allocation_obj.pk}'
        )


def update_user_groups(allocation_user_obj):
    if not ENABLE_GEODE_PROJECT_LDAP_INTEGRATION:
        return

    ldap_conn = LDAPModify()
    is_manager = allocation_user_obj.allocation.project.projectuser_set.filter(
        role__name='Manager', user=allocation_user_obj.user)
    if is_manager:
        add_user(allocation_user_obj, "Storage: Admin Group", ldap_conn)
        remove_user(allocation_user_obj, "Storage: Users Group", ldap_conn)
    else:
        add_user(allocation_user_obj, "Storage: Users Group", ldap_conn)
        remove_user(allocation_user_obj, "Storage: Admin Group", ldap_conn)


class LDAPModify:
    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_GEODE_PROJECT_SERVER_URI')
        self.LDAP_BASE_DN = import_from_settings('LDAP_GEODE_PROJECT_BASE_DN')
        self.LDAP_BIND_DN = import_from_settings('LDAP_GEODE_PROJECT_BIND_DN')
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_GEODE_PROJECT_BIND_PASSWORD')
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_GEODE_PROJECT_CONNECT_TIMEOUT', 2.5)
        self.LDAP_GROUP_TYPE = import_from_settings('LDAP_GEODE_PROJECT_GROUP_TYPE')

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

        if not self.conn.bind():
            logger.error(f'LDAPModify: Failed to bind to LDAP server: {self.conn.result}')

    def add_group(self, group_name, users):
        dn = f'cn={group_name},{self.LDAP_BASE_DN}'
        attributes = {
            'objectClass': ['group', 'top'],
            'sAMAccountName': group_name,
            'groupType': self.LDAP_GROUP_TYPE
        }
        if users:
            attributes['member'] = users
        added = self.conn.add(dn, attributes=attributes)

        return added, self.conn.result.get('description')

    def remove_group(self, group_name):
        dn = f'cn={group_name},{self.LDAP_BASE_DN}'
        removed = self.conn.delete(dn)
        return removed, self.conn.result.get('description')
    
    def add_user(self, group_name, user):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        changes = {
            "member": [(MODIFY_ADD, [user])]
        }
        added = self.conn.modify(dn, changes)
        return added, self.conn.result.get("description")

    def remove_user(self, group_name, user):
        dn = f"cn={group_name},{self.LDAP_BASE_DN}"
        changes = {
            "member": [(MODIFY_DELETE, [user])]
        }
        removed = self.conn.modify(dn, changes)
        return removed, self.conn.result.get("description")
