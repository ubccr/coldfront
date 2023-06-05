import datetime

from coldfront.core.allocation.models import Allocation


def generate_publication_by_year_chart_data(publications_by_year):
    """Generate the data for the publication by year chart
    """

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

def generate_bar_graph():
    pass

def generate_resource_bar_graph(resource_data):

    if resource_data:
        years, storage = zip(*resource_data)
        years = list(years)
        storage = list(storage)
        years.insert(0, "Year")
        storage.insert(0, "Publications")

        data = {
            "x": "Year",
            "columns": [
                years,
                storage
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

def set_conditional_color(usage, free):
    total = [sum(x) for x in zip(usage, free)]
    perc_used = [x[1]/x[0] for x in zip(total, usage)]
    colors = ["#000"]
    for perc in perc_used:
        if perc > 80:
            colors.append("#17a2b8")
        elif perc > 50:
            colors.append("#4a4a4a")
        else:
            colors.append("#17a2b8")
    return colors


def generate_volume_bar_graph(storage_data):

    if storage_data:
        storage_data['names'].insert(0, "names")
        storage_data['usage_TBs'].insert(0, "usage_TBs")
        storage_data['quota_TBs'].insert(0, "quota_TBs")

        data = {
            "x": "names",
            "columns": [
                storage_data['usage_TBs'],
                storage_data['quota_TBs'],
                storage_data['names'],
            ],
            "type": "bar",
            "order": "null",
            "groups": [[
                    'usage_TBs',
                    'quota_TBs',
                    ]],
            "colors": {
                "quota_TBs": '#4a4a4a',
                # "usage_TBs": '#17a2b8',
            },
            "classes": {
                "usage_TBs": "reactive-usage-bar",

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
            "columns": [],
            "type": 'donut',
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
