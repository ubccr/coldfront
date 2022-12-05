import datetime

from django.contrib.auth.models import User
from coldfront.core.allocation.models import Allocation
from coldfront.core.project.models import Project, ProjectUser


def generate_publication_by_year_chart_data(publications_by_year):

    if publications_by_year:
        years, publications = zip(*publications_by_year)
        years = list(years)
        publications = list(publications)
        years.insert(0, "Year")
        publications.insert(0, "Publications")

        data = {
            "x": "Year",
            "columns": [
                years,
                publications
            ],
            "type": "bar",
            "colors": {
                "Publications": '#17a2b8'
            }
        }
    else:
        data = {
            "columns": [],
            "type": 'bar'
        }

    return data


def generate_total_grants_by_agency_chart_data(total_grants_by_agency):

    grants_agency_chart_data = {
        "columns": total_grants_by_agency,
        "type": 'donut'
    }

    return grants_agency_chart_data


def generate_resources_chart_data(allocations_count_by_resource_type):


    if allocations_count_by_resource_type:
        cluster_label = "Cluster: %d" % (allocations_count_by_resource_type.get('Cluster', 0))
        cloud_label = "Cloud: %d" % (allocations_count_by_resource_type.get('Cloud', 0))
        server_label = "Server: %d" % (allocations_count_by_resource_type.get('Server', 0))
        storage_label = "Storage: %d" % (allocations_count_by_resource_type.get('Storage', 0))

        resource_plot_data = {
            "columns": [
                [cluster_label, allocations_count_by_resource_type.get('Cluster', 0)],
                [storage_label, allocations_count_by_resource_type.get('Storage', 0)],
                [cloud_label, allocations_count_by_resource_type.get('Cloud', 0)],
                [server_label, allocations_count_by_resource_type.get('Server', 0)]

            ],
            "type": 'donut',
            "colors": {
                cluster_label: '#6da04b',
                storage_label: '#ffc72c',
                cloud_label: '#2f9fd0',
                server_label: '#e56a54',

            }
        }
    else:
        resource_plot_data = {
            "type": 'donut',
            "columns": []
        }

    return resource_plot_data


def generate_allocations_chart_data():

    active_count = Allocation.objects.filter(status__name='Active').count()
    new_count = Allocation.objects.filter(status__name='New').count()
    renewal_requested_count = Allocation.objects.filter(status__name='Renewal Requested').count()

    now = datetime.datetime.now()
    start_time = datetime.date(now.year - 1, 1, 1)
    expired_count = Allocation.objects.filter(
        status__name='Expired', end_date__gte=start_time).count()

    active_label = "Active: %d" % (active_count)
    new_label = "New: %d" % (new_count)
    renewal_requested_label = "Renewal Requested: %d" % (renewal_requested_count)
    expired_label = "Expired: %d" % (expired_count)

    allocation_chart_data = {
        "columns": [
            [active_label, active_count],
            [new_label, new_count],
            [renewal_requested_label, renewal_requested_count],
            [expired_label, expired_count],
        ],
        "type": 'donut',
        "colors": {
            active_label: '#6da04b',
            new_label: '#2f9fd0',
            renewal_requested_label: '#ffc72c',
            expired_label: '#e56a54',
        }
    }

    return allocation_chart_data


def generate_project_type_chart_data():
    num_research_projects_count = Project.objects.filter(
        status__name__in=['Active', 'Waiting For Admin Approval', 'Review Pending', ],
        type__name='Research'
    ).count()
    num_class_projects_count = Project.objects.filter(
        status__name__in=['Active', 'Waiting For Admin Approval', 'Review Pending', ],
        type__name='Class'
    ).count()

    research_projects_count_label = f'Research: {num_research_projects_count}'
    class_projects_count_label = f'Class: {num_class_projects_count}'

    project_type_chart_data = {
        'columns': [
            [research_projects_count_label, num_research_projects_count],
            [class_projects_count_label, num_class_projects_count],
        ],
        'type': 'donut',
        'colors': {
            research_projects_count_label: '#673ab7',
            class_projects_count_label: '#e27602'
        }
    }

    return project_type_chart_data


def generate_project_status_chart_data():
    num_active_projects = Project.objects.filter(status__name='Active').count()
    num_requested_projects = Project.objects.filter(status__name='Waiting For Admin Approval').count()
    num_renewal_projects = Project.objects.filter(status__name='Review Pending').count()

    active_projects_label = f'Active: {num_active_projects}'
    requested_projects_label = f'Waiting For Admin Approval: {num_requested_projects}'
    renewal_projects = f'Renewal Requested: {num_renewal_projects}'

    project_status_chart_data = {
        'columns': [
            [active_projects_label, num_active_projects],
            [requested_projects_label, num_requested_projects],
            [renewal_projects, num_renewal_projects],
        ],
        'type': 'donut',
        'colors': {
            active_projects_label: '#6da04b',
            requested_projects_label: '#2f9fd0',
            renewal_projects: '#ffc72c'
        }
    }

    return project_status_chart_data


def generate_research_project_status_columns():
    research_projects = Project.objects.filter(type__name='Research')
    num_active_projects = research_projects.filter(status__name='Active').count()
    num_requested_projects = research_projects.filter(status__name='Waiting For Admin Approval').count()
    num_renewal_projects = research_projects.filter(status__name='Review Pending').count()

    active_projects_label = f'Active (R): {num_active_projects}'
    requested_projects_label = f'Waiting For Admin Approval (R): {num_requested_projects}'
    renewal_projects = f'Renewal Requested (R): {num_renewal_projects}'

    research_project_status_columns = {
        'columns': [
            [active_projects_label, num_active_projects],
            [requested_projects_label, num_requested_projects],
            [renewal_projects, num_renewal_projects],
        ],
        'colors': {
            active_projects_label: '#6da04b',
            requested_projects_label: '#2f9fd0',
            renewal_projects: '#ffc72c'
        }
    }

    return research_project_status_columns


def generate_class_project_status_columns():
    research_projects = Project.objects.filter(type__name='Class')
    num_active_projects = research_projects.filter(status__name='Active').count()
    num_requested_projects = research_projects.filter(status__name='Waiting For Admin Approval').count()
    num_renewal_projects = research_projects.filter(status__name='Review Pending').count()

    active_projects_label = f'Active (C): {num_active_projects}'
    requested_projects_label = f'Waiting For Admin Approval (C): {num_requested_projects}'
    renewal_projects = f'Renewal Requested (C): {num_renewal_projects}'

    class_project_status_columns = {
        'columns': [
            [active_projects_label, num_active_projects],
            [requested_projects_label, num_requested_projects],
            [renewal_projects, num_renewal_projects]
        ],
        'colors': {
            active_projects_label: '#6da04b',
            requested_projects_label: '#2f9fd0',
            renewal_projects: '#ffc72c'
        }
    }

    return class_project_status_columns


def generate_user_counts():
    project_statuses = ['Active', 'Waiting For Admin Approval', 'Review Pending', ]
    num_unique_active_users = len(set(ProjectUser.objects.filter(
        status__name='Active',
        project__status__name__in=project_statuses
    ).values_list('user', flat=True)))
    num_unique_active_pis = len({
        project.pi for project in Project.objects.filter(status__name__in=project_statuses)
    })

    unique_user_label = f'Unique Active Users: {num_unique_active_users}'
    unique_pi_label = f'Unique Active PIs: {num_unique_active_pis}'

    user_counts_chart_data = {
        'columns': [
            [unique_user_label, num_unique_active_users],
            [unique_pi_label, num_unique_active_pis],
        ],
        'type': 'bar',
        'colors': {
            unique_pi_label: '#2f9fd0',
            unique_user_label: '#6da04b'
        }
    }

    return user_counts_chart_data


def create_months():
    months = {
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 0,
        '5': 0,
        '6': 0,
        '7': 0,
        '8': 0,
        '9': 0,
        '10': 0,
        '11': 0,
        '12': 0,
    }

    return months


def create_years(start, stop):
    years = {}
    for year in range(start, stop + 1):
        years[str(year)] = {
            'months': create_months(),
            'total_new_users': 0,
        }

    return years


def generate_user_timeline():
    unique_users = User.objects.all().order_by('date_joined')
    start_year = unique_users[0].date_joined.year
    stop_years = unique_users[unique_users.count() - 1].date_joined.year
    years = create_years(start_year, stop_years)
    for count, user in enumerate(unique_users, start=1):
        date_joined = user.date_joined
        year = str(date_joined.year)
        month = str(date_joined.month)
        years[year]['months'][month] = count
        years[year]['total_new_users'] = count

    year_list = [year + '-01-01' for year in years.keys()]
    year_list = [f'{start_year - 1}-01-01'] + year_list
    year_label = 'Years'
    year_new_users_list = [values['total_new_users'] for values in years.values()]
    year_new_users_list = [0] + year_new_users_list
    year_new_users_label = 'Total Unique Users'

    years_to_months_labels = {}
    years_to_months_values = {}
    total_users = 0
    current_date = datetime.datetime.today()
    current_month = current_date.month
    current_year = current_date.year
    for year, months_and_total in years.items():
        months = months_and_total['months']
        years_to_months_labels[year] = ['Months']
        years_to_months_values[year] = [f'Total Unique Users ({year})']
        for month, users in months.items():
            if int(year) == current_year and int(month) > current_month:
                continue
            years_to_months_labels[year].append(year + '-' + month + '-01')
            if users < 1:
                users = total_users
            years_to_months_values[year].append(users)
            total_users = users

    user_timeline_chart_data = {
        'x': year_label,
        'columns': [
            [year_label] + year_list,
            [year_new_users_label] + year_new_users_list,
        ]
    }

    return user_timeline_chart_data, years_to_months_labels, years_to_months_values
