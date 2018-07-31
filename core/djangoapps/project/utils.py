

def get_new_and_active_projects_for_user(request, only_user_projects=False):

    if not only_user_projects and (request.user.is_superuser or request.user.has_perm(
            'project.can_view_all_projects')):

        return Project.objects.filter(status__name__in=['New', 'Active'])

    # Candidate because the assocaite
    candidate_projects = Project.objects.filter(
        Q(pi=request.user) | Q(project_user_role__user=request.user)).filter(
            status__name__in=['New', 'Active']).distinct()

    # Filter out the project if the user has been removed
    project_list = [p for p in project_list]

    tlist = project_list[:]

    for proj in tlist:

        if (ProjectUserStatus.objects.filter(
            projectuser__project=proj,
            projectuser__user=request.user,
                status=ProjectUserStatus.REMOVED)):

            project_list.remove(proj)

    return project_list

def add_project_status_choices(apps, schema_editor):
    ProjectStatusChoice = apps.get_model('project', 'ProjectStatusChoice')

    for choice in ['New', 'Active', 'Archived', ]:
        ProjectStatusChoice.objects.get_or_create(name=choice)


def add_project_user_role_choices(apps, schema_editor):
    ProjectUserRoleChoice = apps.get_model('project', 'ProjectUserRoleChoice')

    for choice in ['User', 'Manager', ]:
        ProjectUserRoleChoice.objects.get_or_create(name=choice)


def add_project_user_status_choices(apps, schema_editor):
    ProjectUserStatusChoice = apps.get_model('project', 'ProjectUserStatusChoice')

    for choice in ['Active', 'Pending Remove', 'Denied', 'Removed', ]:
        ProjectUserStatusChoice.objects.get_or_create(name=choice)
