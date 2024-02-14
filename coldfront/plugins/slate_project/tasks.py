import logging

from coldfront.core.allocation.models import Allocation, AllocationUser, AllocationUserStatusChoice
from coldfront.plugins.slate_project.utils import (sync_slate_project_users,
                                                   sync_slate_project_ldap_group,
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
        allocation__status__name='Active',
        status__name__in=['Active', 'Eligible', 'Disabled', 'Retired']
    ).select_related('user', 'status', 'allocation', 'allocation__project')
    status_objs = {
        'Active': AllocationUserStatusChoice.objects.get(name='Active'),
        'Eligible': AllocationUserStatusChoice.objects.get(name='Eligible'),
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
