import datetime

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


def generate_user_role_counts():
    num_active_users = ProjectUser.objects.filter(status__name='Active', role__name='User').count()
    active_managers = ProjectUser.objects.filter(status__name='Active', role__name='Manager')
    num_active_managers = 0
    num_active_pis = 0
    for manager in active_managers:
        if manager.project.pi == manager.user:
            num_active_pis += 1
        else:
            num_active_managers += 1

    num_active_users += num_active_managers
    user_label = f'Total Active Users: {num_active_users}'
    pi_label = f'Total Active PIs: {num_active_pis}'

    user_counts_chart_data = {
        'columns': [
            [user_label, num_active_users],
            [pi_label, num_active_pis],
        ],
        'type': 'donut',
        'colors': {
            user_label: '#ffc72c',
            pi_label: '#6da04b',
        }
    }

    return user_counts_chart_data


def generate_user_counts():
    num_unique_active_users = len(set(ProjectUser.objects.filter(status__name='Active').values_list('user', flat=True)))
    num_unique_active_pis = len({project.pi for project in Project.objects.all()})
    num_active_users = ProjectUser.objects.filter(status__name='Active').count()

    unique_user_label = f'Unique Active Users: {num_unique_active_users}'
    unique_pi_label = f'Unique Active PIs: {num_unique_active_pis}'
    user_label = f'Total Active Users: {num_active_users}'

    user_counts_chart_data = {
        'columns': [
            [unique_user_label, num_unique_active_users],
            [unique_pi_label, num_unique_active_pis],
            [user_label, num_active_users],
        ],
        'type': 'bar',
        'colors': {
            user_label: '#673ab7',
            unique_pi_label: '#285424',
            unique_user_label: '#e27602'
        }
    }

    return user_counts_chart_data
