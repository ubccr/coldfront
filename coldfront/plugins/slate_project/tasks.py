import logging

from coldfront.core.allocation.models import Allocation, AllocationUser, AllocationUserStatusChoice
from coldfront.plugins.slate_project.utils import (sync_slate_project_users,
                                                   sync_slate_project_ldap_group,
                                                   sync_user_statuses,
                                                   send_ineligible_users_report,
                                                   send_ineligible_pis_report,
                                                   import_slate_projects,
                                                   get_new_user_status,
                                                   send_access_removed_email,
                                                   LDAPModify,
                                                   LDAPImportSearch)

logger = logging.getLogger(__name__)


def sync_all_slate_project_allocations():
    slate_project_allocation_objs = Allocation.objects.filter(
        resources__name='Slate Project', status__name__in=['Active', 'Renewal Requested']
    )
    ldap_conn = LDAPModify()
    ldap_search_conn = LDAPImportSearch()
    logger.info('Running sync...')
    for slate_project_allocation_obj in slate_project_allocation_objs:
        sync_slate_project_ldap_group(slate_project_allocation_obj, ldap_conn)
        sync_slate_project_users(slate_project_allocation_obj, ldap_conn, ldap_search_conn)
    logger.info('Sync complete')


def send_ineligible_users_email_report():
    send_ineligible_users_report()


def send_ineligible_pis_email_report():
    send_ineligible_pis_report()


def import_new_slate_projects(json, out):
    import_slate_projects(json_file_name = json, out_file_name = out)


def update_all_user_statuses():
    slate_project_user_objs = AllocationUser.objects.filter(
        allocation__resources__name='Slate Project',
        allocation__status__name__in=['Active', 'Renewal Requested'],
        status__name__in=['Active', 'Eligible', 'Disabled', 'Retired']
    ).select_related('user', 'status', 'allocation', 'allocation__project')
    sync_user_statuses(slate_project_user_objs)
