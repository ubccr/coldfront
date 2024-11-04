import logging

from coldfront.core.allocation.models import Allocation, AllocationAttributeType, AllocationUser
from coldfront.plugins.slate_project.utils import (sync_slate_project_users,
                                                   sync_slate_project_ldap_group,
                                                   sync_slate_project_user_statuses,
                                                   sync_slate_project_allocated_quantities,
                                                   send_ineligible_users_report,
                                                   send_ineligible_pis_report,
                                                   import_slate_projects,
                                                   create_slate_project_data_file,
                                                   send_slate_project_data_file,
                                                   download_files,
                                                   check_slate_project_owner_aginst_current_pi,
                                                   sync_smb_status,
                                                   LDAPModify,
                                                   LDAPImportSearch)

logger = logging.getLogger(__name__)


def check_for_mismatch_owner_and_pi():
    ldap_conn = LDAPModify()
    allocation_objs = Allocation.objects.filter(
        resources__name='Slate Project', status__name='Active')

    for allocation_obj in allocation_objs:
        check_slate_project_owner_aginst_current_pi(allocation_obj, ldap_conn)


def sync_all_slate_project_allocations():
    slate_project_allocation_objs = Allocation.objects.filter(
        resources__name='Slate Project', status__name__in=['Active', 'Renewal Requested']
    )
    allocation_attribute_type_obj = AllocationAttributeType.objects.get('SMB Enabled')
    ldap_conn = LDAPModify()
    ldap_search_conn = LDAPImportSearch()
    logger.info('Running sync...')
    for slate_project_allocation_obj in slate_project_allocation_objs:
        sync_slate_project_ldap_group(slate_project_allocation_obj, ldap_conn)
        sync_slate_project_users(slate_project_allocation_obj, ldap_conn, ldap_search_conn)
        sync_smb_status(slate_project_allocation_obj, allocation_attribute_type_obj, ldap_conn)
    logger.info('Sync complete')


def sync_all_slate_project_allocated_quantities():
    sync_slate_project_allocated_quantities()


def download_all_files():
    download_files()


def send_ineligible_users_email_report():
    send_ineligible_users_report()


def send_ineligible_pis_email_report():
    send_ineligible_pis_report()


def import_new_slate_projects(json, out, user):
    import_slate_projects(json, out, user)


def update_all_user_statuses():
    slate_project_user_objs = AllocationUser.objects.filter(
        allocation__resources__name='Slate Project',
        allocation__status__name__in=['Active', 'Renewal Requested'],
        status__name__in=['Active', 'Eligible', 'Disabled', 'Retired']
    ).select_related('user', 'status', 'allocation', 'allocation__project')
    sync_slate_project_user_statuses(slate_project_user_objs)


def create_slate_project_data():
    slate_project_filename = create_slate_project_data_file()
    send_slate_project_data_file(slate_project_filename)