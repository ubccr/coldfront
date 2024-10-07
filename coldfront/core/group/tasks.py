from django.contrib.auth.models import Group
from coldfront.core.user.models import User
from coldfront.core.project.models import (
    Project,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)


def grant_usersupport_global_project_manager() -> None:
    """
    Grant the RIS-UserSupport group Manager status over all Projects
    """

    # If the group does not exist raise an exception
    group_name = "RIS-UserSupport"
    group = Group.objects.filter(name=group_name).first()
    if not group:
        raise ValueError(f"Group {group_name} not found")

    # If the role or status choices do not exist raise an exception
    role_name = "Manager"
    status_name = "Active"
    project_user_role = ProjectUserRoleChoice.objects.filter(name=role_name).first()
    project_user_status = ProjectUserStatusChoice.objects.filter(
        name=status_name
    ).first()
    if not project_user_role and project_user_status:
        raise ValueError(
            f"ProjectUserRole {role_name} or ProjectUserStatus {status_name} not found"
        )

    # If no projects found raise and exception
    all_projects = Project.objects.all()
    if not all_projects:
        raise ValueError("No projects found")
    group_users = User.objects.filter(groups=group)

    # Iterate over all projects
    for project in all_projects:
        project_users = ProjectUser.objects.filter(
            project=project, user__in=group_users
        )
        existing_project_users = {pu.user_id: pu for pu in project_users}

        new_project_users = []
        updated_project_users = []
        # Iterate over all users in the group
        for user in group_users:
            # If the user is already in the project, update their role and status
            if user.id in existing_project_users:
                project_user = existing_project_users[user.id]
                project_user.role = project_user_role
                project_user.status = project_user_status
                project_user.enable_notifications = True
                updated_project_users.append(project_user)
            # Otherwise, add the user to the project
            else:
                new_project_users.append(
                    ProjectUser(
                        project=project,
                        user=user,
                        role=project_user_role,
                        status=project_user_status,
                        enable_notifications=True,
                    )
                )

        # Bulk update the project users
        if updated_project_users:
            ProjectUser.objects.bulk_update(
                updated_project_users, ["role", "status", "enable_notifications"]
            )
        # Bulk create the new project users
        if new_project_users:
            ProjectUser.objects.bulk_create(new_project_users)
