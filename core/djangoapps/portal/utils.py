
import datetime

from core.djangoapps.subscription.models import Subscription


def generate_publication_by_year_chart_data(publications_by_year):

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

    return data


def generate_total_grants_by_agency_chart_data(total_grants_by_agency):

    grants_agency_chart_data = {
        "columns": total_grants_by_agency,
        "type": 'donut'
    }


    return grants_agency_chart_data



def generate_resources_chart_data(subscriptions_count_by_resource_type):

    cluster_label = "Cluster: %d" % (subscriptions_count_by_resource_type['Cluster'])
    cloud_label = "Cloud: %d" % (subscriptions_count_by_resource_type['Cloud'])
    server_label = "Server: %d" % (subscriptions_count_by_resource_type['Server'])
    storage_label = "Storage: %d" % (subscriptions_count_by_resource_type['Storage'])

    resource_plot_data = {
        "columns": [
            [cluster_label, subscriptions_count_by_resource_type['Cluster']],
            [storage_label, subscriptions_count_by_resource_type['Storage']],
            [cloud_label, subscriptions_count_by_resource_type['Cloud']],
            [server_label, subscriptions_count_by_resource_type['Server']],

        ],
        "type": 'donut',
        "colors": {
            cluster_label: '#6da04b',
            storage_label: '#ffc72c',
            cloud_label: '#2f9fd0',
            server_label: '#e56a54',

        }
    }

    return resource_plot_data


def generate_subscriptions_chart_data():

    active_count = Subscription.objects.filter(status__name='Active').count()
    new_count = Subscription.objects.filter(status__name='New').count()
    pending_count = Subscription.objects.filter(status__name='Pending').count()


    now = datetime.datetime.now()
    start_time = datetime.date(now.year - 1, 1, 1)
    # start_time = datetime.date(now.year-1, now.month, now.day)
    expired_count = Subscription.objects.filter(
        status__name='Expired', active_until__gte=start_time).count()
    # expired_count = Subscription.objects.filter(status='EXP').count()

    active_label = "Active: %d" % (active_count)
    new_label = "New: %d" % (new_count)
    pending_label = "Pending: %d" % (pending_count)
    expired_label = "Expired: %d" % (expired_count)


    subscription_chart_data = {
        "columns": [
            [active_label, active_count],
            [new_label, new_count],
            [pending_label, pending_count],
            [expired_label, expired_count],
        ],
        "type": 'donut',
        "colors": {
            active_label: '#6da04b',
            new_label: '#2f9fd0',
            pending_label: '#ffc72c',
            expired_label: '#e56a54',
        }
    }

    return subscription_chart_data
