import datetime


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
