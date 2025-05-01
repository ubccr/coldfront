from django.urls import path

from coldfront.plugins.qumulo.views import (
    allocation_view,
    update_allocation_view,
    create_sub_allocation_view,
    allocation_table_view,
    trigger_migrations_view,
    user_management_view,
)
from coldfront.plugins.qumulo.api.allocations import Allocations
from coldfront.plugins.qumulo.api.active_directory_members import ActiveDirectoryMembers


app_name = "qumulo"
urlpatterns = [
    path("allocation", allocation_view.AllocationView.as_view(), name="allocation"),
    path(
        "allocation/<int:allocation_id>/",
        update_allocation_view.UpdateAllocationView.as_view(),
        name="updateAllocation",
    ),
    path(
        "allocation/<int:allocation_id>/sub_allocation/",
        create_sub_allocation_view.CreateSubAllocationView.as_view(),
        name="createSubAllocation",
    ),
    path(
        "allocation-table-list",
        allocation_table_view.AllocationTableView.as_view(),
        name="allocation-table-list",
    ),
    path(
        "trigger-migrations",
        trigger_migrations_view.TriggerMigrationsView.as_view(),
        name="trigger-migrations",
    ),
    path(
        "allocation-admin/user-access-management",
        user_management_view.UserAccessManagementView.as_view(),
        name="user-access-management",
    ),
    path("api/allocations", Allocations.as_view(), name="getAllocations"),
    path(
        "api/active-directory-members",
        ActiveDirectoryMembers.as_view(),
        name="getActiveDirectoryMembers",
    ),
]
