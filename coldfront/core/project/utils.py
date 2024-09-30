import datetime

from django.forms.models import model_to_dict

from coldfront.core.project.models import ProjectAdminAction, ProjectStatusChoice


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


def get_new_end_date_from_list(expire_dates, check_date=None, buffer_days=0):
    """
    Finds a new end date based on the given list of expire dates.

    :param expire_dates: List of expire dates
    :param check_date: Date that is checked against the list of expire dates. If None then it's
    set to today
    :param buffer_days: Number of days before the current expire date where the end date should be
    set to the next expire date
    :return: A new end date
    """
    if check_date is None:
        check_date = datetime.date.today()

    expire_dates.sort()

    buffer_dates = [date - datetime.timedelta(days=buffer_days) for date in expire_dates]

    end_date = None
    total_dates = len(expire_dates)
    for i in range(total_dates):
        if check_date < expire_dates[i]:
            if check_date >= buffer_dates[i]:
                end_date = expire_dates[(i + 1) % total_dates]
                if (i + 1) % total_dates == 0:
                    end_date = end_date.replace(end_date.year + 1)
            else:
                end_date = expire_dates[i]
            break
        elif i == total_dates - 1:
            expire_date = expire_dates[0]
            end_date = expire_date.replace(expire_date.year + 1)

    return end_date


def create_admin_action(user, fields_to_check, project, base_model=None):
    if base_model is None:
        base_model = project
    base_model_dict = model_to_dict(base_model)

    for key, value in fields_to_check.items():
        project_value = base_model_dict.get(key)
        if type(value) is not type(project_value):
            if key == 'status':
                project_value = ProjectStatusChoice.objects.get(pk=project_value).name
                value = value.name
        if value != project_value:
            ProjectAdminAction.objects.create(
                user=user,
                project=project,
                action=f'Changed "{key}" from "{project_value}" to "{value}"'
            )


def get_project_user_emails(project_obj, only_project_managers=False):
    """
    Returns a list of project user emails in the given project. Only emails from users with their
    notifications enabled will be returned.

    :param allocation_obj: The project to grab the project user emails from
    :param only_project_managers: Indicates if only the project manager emails should be returned
    """
    project_users = project_obj.projectuser_set.filter(
        enable_notifications=True,
        status__name__in=['Active', 'Pending - Remove']
    )
    if only_project_managers:
        project_users = project_users.filter(role__name='Manager')
    project_users = project_users.values_list('user__email', flat=True)


    return list(project_users)


def generate_slurm_account_name(project_obj):
    num = str(project_obj.pk)
    string = '00000'
    string = string[:-len(num)] + num
    project_type = project_obj.type.name
    letter = 'r'
    if project_type == 'Class':
        letter = 'c'

    return letter + string


def create_admin_action_for_deletion(user, deleted_obj, project, base_model=None):
    if base_model:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Deleted "{deleted_obj}" from "{base_model}" in "{project}"'
        )
    else:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Deleted "{deleted_obj}" from "{project}"'
        )


def create_admin_action_for_creation(user, created_obj, project, base_model=None):
    if base_model:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Created "{created_obj}" in "{base_model}" in "{project}"'
        )
    else:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Created "{created_obj}" in "{project}"'
        )