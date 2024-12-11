from django.dispatch import receiver

from coldfront.core.project.signals import project_activate, project_user_role_changed
from coldfront.core.project.views import ProjectActivateRequestView, ProjectUserDetail
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.allocation.signals import allocation_activate, allocation_activate_user, allocation_remove, allocation_remove_user
from coldfront.core.allocation.models import Allocation, AllocationUser
from coldfront.core.allocation.views import (AllocationDetailView,
                                             AllocationAddUsersView,
                                             AllocationRemoveUsersView,
                                             AllocationRemoveView,
                                             AllocationApproveRemovalRequestView)
from coldfront.plugins.geode_project import utils


@receiver(project_activate, sender=ProjectActivateRequestView)
def send_allocation_request_email(sender, **kwargs):
    project_pk = kwargs.get('project_pk')
    project_obj = Project.objects.get(pk=project_pk)

    utils.send_new_allocation_request_email(project_obj)


@receiver(allocation_activate, sender=AllocationDetailView)
def add_groups(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Geode-Projects':
        return
    if not allocation_obj.status.name == 'Active':
        return

    utils.add_groups(allocation_obj)


@receiver(allocation_remove, sender=AllocationRemoveView)
@receiver(allocation_remove, sender=AllocationApproveRemovalRequestView)
def remove_groups(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Geode-Projects':
        return
    if not allocation_obj.status.name == 'Removed':
        return

    utils.remove_groups(allocation_obj)


@receiver(allocation_activate_user, sender=AllocationAddUsersView)
def add_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Geode-Projects':
        return
    if not allocation_user_obj.allocation.status.name in ['Active', 'Renewal Requested', ]:
        return

    utils.add_user(allocation_user_obj)


@receiver(allocation_remove_user, sender=AllocationRemoveUsersView)
def remove_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Geode-Projects':
        return
    if not allocation_user_obj.allocation.status.name in ['Active', 'Renewal Requested', ]:
        return

    utils.remove_user(allocation_user_obj)


@receiver(project_user_role_changed, sender=ProjectUserDetail)
def change_user_group(sender, **kwargs):
    project_user_pk = kwargs.get('project_user_pk')
    project_user_obj = ProjectUser.objects.get(pk=project_user_pk)
    project_obj = project_user_obj.project
    geode_project_allocation_obj = project_obj.allocation_set.filter(
        resources__name='Geode-Projects', status__name__in=['Active', 'Renewal Requested', ])
    if not geode_project_allocation_obj.exists():
        return
    allocation_user_obj = geode_project_allocation_obj[0].allocationuser_set.filter(user=project_user_obj.user, status__name='Active')
    if not allocation_user_obj.exists():
        return

    allocation_user_obj = allocation_user_obj[0]
    utils.update_user_groups(allocation_user_obj)
