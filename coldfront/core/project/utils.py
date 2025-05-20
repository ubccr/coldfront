import logging
import datetime

from django.forms.models import model_to_dict

from coldfront.core.project.models import ProjectAdminAction, Project
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.ldap_user_info.utils import get_user_info, get_users_info

PROJECT_PI_ELIGIBLE_ADS_GROUPS = import_from_settings('PROJECT_PI_ELIGIBLE_ADS_GROUPS', [])

logger = logging.getLogger(__name__)


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
        base_model_value = base_model_dict.get(key)
        if type(value) is not type(base_model_value):
            if key == 'status':
                status_class = base_model._meta.get_field('status').remote_field.model
                base_model_value = status_class.objects.get(pk=base_model_value).name
                value = value.name
        if value != base_model_value:
            if type(base_model) == Project:
                action = f'Changed "{key}" from "{base_model_value}" to "{value}"'
            else:
                action = f'For "{base_model}" changed "{key}" from "{base_model_value}" to "{value}"'
            ProjectAdminAction.objects.create(
                user=user,
                project=project,
                action=action
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
    letter = project_obj.type.name.lower()[0]

    return letter + string


def create_admin_action_for_deletion(user, deleted_obj, project, base_model=None):
    if base_model:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Deleted "{deleted_obj}" from "{base_model}"'
        )
    else:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Deleted "{deleted_obj}"'
        )


def create_admin_action_for_creation(user, created_obj, project, base_model=None):
    if base_model:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Created "{created_obj}" in "{base_model}" with value "{created_obj.value}"'
        )
    else:
        ProjectAdminAction.objects.create(
            user=user,
            project=project,
            action=f'Created "{created_obj}" with value "{created_obj.value}"'
        )


def create_admin_action_for_project_creation(user, project):
    ProjectAdminAction.objects.create(
        user=user,
        project=project,
        action=f'Created a project with status "{project.status.name}"'
    )


def check_if_pi_eligible(user, memberships=None):
    if not PROJECT_PI_ELIGIBLE_ADS_GROUPS:
        return True

    if not memberships:
        memberships = get_user_info(user.username, ['memberOf']).get('memberOf')

    if not memberships:
        return False

    for membership in memberships:
        if membership in PROJECT_PI_ELIGIBLE_ADS_GROUPS:
            return True

    return False


def check_if_pis_eligible(users):
    if not PROJECT_PI_ELIGIBLE_ADS_GROUPS:
        return {}

    usernames = [user.username for user in set(users)]
    eligible_statuses = {}
    memberships = get_users_info(usernames, ['memberOf'])
    for user, user_memberships in memberships.items():
        for user_membersip in user_memberships.get('memberOf'):
            eligible = user_membersip in PROJECT_PI_ELIGIBLE_ADS_GROUPS
            eligible_statuses[user] = eligible
            if eligible:
                break

    return eligible_statuses