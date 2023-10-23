import logging
import ldap.filter
from ldap3 import Connection, Server

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import ProjectUserStatusChoice, Project
from coldfront.core.allocation.models import AllocationUserStatusChoice, Allocation

logger = logging.getLogger(__name__)


def check_inactive_project_user_with_ldap(project_pk):
    project_obj = Project.objects.get(pk=project_pk)
    allocation_objs = project_obj.allocation_set.filter(status__name='Active')
    project_user_objs = project_obj.projectuser_set.filter(status__name='Active')
    ldap_search = LDAPSearch()
    for project_user_obj in project_user_objs:
        user_obj = project_user_obj.user
        result = ldap_search.search_a_user(user_obj.username, ['title'])
        if not result:
            project_user_obj.status = ProjectUserStatusChoice.objects.get(name='Inactive')
            project_user_obj.save()
            logger.info(
                f'Project user {user_obj.username} has become inactive (project pk={project_pk})'
            )
        
            for allocation_obj in allocation_objs:
                allocation_user_obj = allocation_obj.allocationuser_set.filter(
                    status__name='Active', user=user_obj
                )
                if allocation_user_obj.exists():
                    allocation_user_obj = allocation_user_obj[0]
                    allocation_user_obj.status = AllocationUserStatusChoice.objects.get(name='Inactive')
                    allocation_user_obj.save()
                    logger.info(
                        f'Allocation user {user_obj.username} has become inactive (allocation '
                        f'pk={allocation_obj.pk})'
                    )

def check_inactive_allocation_user_with_ldap(allocation_pk):
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    project_obj = allocation_obj.project
    check_inactive_project_user_with_ldap(project_obj.pk)


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
        return self.conn.entries