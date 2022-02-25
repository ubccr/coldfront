from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import set_project_allocation_value
from coldfront.api.statistics.utils import set_project_usage_value
from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.api.statistics.utils import set_project_user_usage_value
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware


def set_service_units(project, allocation_objects, updated_su, reason,
                      update_usage):
    """
    Sets allocation and allocation_user service units to updated_su. Creates
    the relevant transaction objects to record the change. Updates the
    relevant historical objects with the reason for the SU change. If
    update_usage is True, allocation and allocation_user usage values are
    updated.
    """

    def set_historical_reason(obj):
        """Set the latest historical object reason"""
        obj.refresh_from_db()
        historical_obj = obj.history.latest('id')
        historical_obj.history_change_reason = reason
        historical_obj.save()

    current_date = utc_now_offset_aware()

    # Set the value for the Project.
    set_project_allocation_value(project, updated_su)

    if update_usage:
        set_project_usage_value(project, updated_su)

    # Create a transaction to record the change.
    ProjectTransaction.objects.create(
        project=project,
        date_time=current_date,
        allocation=updated_su)

    # Set the reason for the change in the newly-created historical object.
    set_historical_reason(
        allocation_objects.allocation_attribute)

    # Do the same for each ProjectUser.
    for project_user in project.projectuser_set.all():
        user = project_user.user
        # Attempt to set the value for the ProjectUser. The method returns
        # whether it succeeded; it may not because not every ProjectUser has a
        # corresponding AllocationUser (e.g., PIs). Only proceed with further
        # steps if an update occurred.
        allocation_updated = set_project_user_allocation_value(
            user, project, updated_su)
        success_flag = allocation_updated

        if update_usage:
            allocation_usage_updated = set_project_user_usage_value(
                user, project, updated_su)

            success_flag = allocation_updated and allocation_usage_updated

        if success_flag:
            # Create a transaction to record the change.
            ProjectUserTransaction.objects.create(
                project_user=project_user,
                date_time=current_date,
                allocation=updated_su)

            # Set the reason for the change in the newly-created historical
            # object.
            allocation_user_obj = get_accounting_allocation_objects(
                project, user=user)
            set_historical_reason(
                allocation_user_obj.allocation_user_attribute)
