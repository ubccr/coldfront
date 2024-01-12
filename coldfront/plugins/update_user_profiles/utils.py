import json
import logging
import ldap.filter
from ldap3 import Connection, Server

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import ProjectUserStatusChoice, ProjectUser
from coldfront.core.allocation.models import AllocationUserStatusChoice, AllocationUser
from coldfront.core.user.models import UserProfile

logger = logging.getLogger(__name__)


def update_all_user_profiles():
    """
    Updates all user profiles and if a user cannot be found in LDAP or has a certain title then
    that user's status in projects and allocations is set to Inactive.
    """
    ldap_search = LDAPSearch()
    user_profiles = UserProfile.objects.all().prefetch_related('user')
    project_user_inactive_status = ProjectUserStatusChoice.objects.get(name='Inactive')
    allocation_user_inactive_status = AllocationUserStatusChoice.objects.get(name='Inactive')
    for user_profile in user_profiles:
        current_title = user_profile.title
        current_department = user_profile.department
        attributes = ldap_search.search_a_user(user_profile.user.username, ['title', 'department'])
        title = attributes.get('title')
        if title:
            title = title[0]
        else:
            title = ''
        department = attributes.get('department')
        if department:
            department = department[0]
        else:
            department = ''
        if title != current_title or department != current_department:
            user_profile.title = title
            user_profile.department = department
            user_profile.save()

        if not title or title in ['Former Employee', 'Retired Staff']:
            project_pks = []
            project_users = ProjectUser.objects.filter(
                user=user_profile.user, project__status__name='Active', status__name='Active'
            )
            for project_user in project_users:
                project_user.status = project_user_inactive_status
                project_user.save()
                project_pks.append(project_user.project.pk)

            allocation_pks = []
            allocation_users = AllocationUser.objects.filter(
                user=user_profile.user, allocation__status__name='Active', status__name='Active'
            )
            for allocation_user in allocation_users:
                allocation_user.status = allocation_user_inactive_status
                allocation_user.save()
                allocation_pks.append(allocation_user.allocation.pk)

            if project_pks:
                project_pks = map(str, project_pks)
                logger.info(
                    f'User {user_profile.user.username}\'s status was set to Inactive in projects '
                    f'{", ".join(project_pks)}'
                )

            if allocation_pks:
                allocation_pks = map(str, allocation_pks)
                logger.info(
                    f'User {user_profile.user.username}\'s status was set to Inactive in allocations '
                    f'{", ".join(allocation_pks)}'
                )


class LDAPSearch:
    search_source = 'LDAP'

    def __init__(self):
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=True, connect_timeout=self.LDAP_CONNECT_TIMEOUT)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def search_a_user(self, user_search_string=None, search_attributes_list=None):
        # Add check if debug is true to run this. If debug is not then write an error to log file.
        assert type(search_attributes_list) is list, 'search_attributes_list should be a list'

        if type(user_search_string) is not str:
            return dict.fromkeys(search_attributes_list, None)

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': ldap.filter.filter_format("(cn=%s)", [user_search_string]),
                            'attributes': search_attributes_list,
                            'size_limit': 1}
        self.conn.search(**searchParameters)
        if self.conn.entries:
            attributes = json.loads(self.conn.entries[0].entry_to_json()).get('attributes')
        else:
            attributes = dict.fromkeys(search_attributes_list, [''])

        return attributes