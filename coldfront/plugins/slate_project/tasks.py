from coldfront.core.allocation.models import Allocation
from coldfront.plugins.slate_project.utils import (sync_slate_project_users,
                                                   send_inactive_users_report,
                                                   LDAPModify)


def sync_all_slate_project_allocations():
    slate_project_allocations = Allocation.objects.filter(
        resources__name='Slate Project', status__name__in=['Active', 'Renewal Requested']
    )
    ldap_conn = LDAPModify()
    for slate_project_allocation in slate_project_allocations:
        sync_slate_project_users(slate_project_allocation, ldap_conn)


def send_inactive_user_email_report():
    send_inactive_users_report()
    