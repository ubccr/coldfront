from django.dispatch import receiver

from coldfront.core.project.views import ProjectDetailView
from coldfront.core.project.signals import visit_project_detail
from coldfront.core.allocation.views import AllocationDetailView
from coldfront.core.allocation.signals import visit_allocation_detail
from coldfront.plugins.check_inactive_users.utils import (check_inactive_project_user_with_ldap,
                                                          check_inactive_allocation_user_with_ldap)

@receiver(visit_project_detail, sender=ProjectDetailView)
def check_inactive_project_users(sender, **kwargs):
    project_pk = kwargs.get('project_pk')
    check_inactive_project_user_with_ldap(project_pk)

@receiver(visit_allocation_detail, sender=AllocationDetailView)
def check_inactive_allocation_users(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    check_inactive_allocation_user_with_ldap(allocation_pk)