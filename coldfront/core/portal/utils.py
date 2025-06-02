# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from coldfront.core.allocation.models import Allocation


def generate_publication_by_year_chart_data(publications_by_year):
    if publications_by_year:
        years, publications = zip(*publications_by_year)
        years = list(years)
        publications = list(publications)
        years.insert(0, "Year")
        publications.insert(0, "Publications")

        data = {"x": "Year", "columns": [years, publications], "type": "bar", "colors": {"Publications": "#17a2b8"}}
    else:
        data = {"columns": [], "type": "bar"}

    return data


def generate_total_grants_by_agency_chart_data(total_grants_by_agency):
    grants_agency_chart_data = {"columns": total_grants_by_agency, "type": "donut"}

    return grants_agency_chart_data


def generate_resources_chart_data(allocations_count_by_resource_type):
    if allocations_count_by_resource_type:
        cluster_label = "Cluster: %d" % (allocations_count_by_resource_type.get("Cluster", 0))
        cloud_label = "Cloud: %d" % (allocations_count_by_resource_type.get("Cloud", 0))
        server_label = "Server: %d" % (allocations_count_by_resource_type.get("Server", 0))
        storage_label = "Storage: %d" % (allocations_count_by_resource_type.get("Storage", 0))

        resource_plot_data = {
            "columns": [
                [cluster_label, allocations_count_by_resource_type.get("Cluster", 0)],
                [storage_label, allocations_count_by_resource_type.get("Storage", 0)],
                [cloud_label, allocations_count_by_resource_type.get("Cloud", 0)],
                [server_label, allocations_count_by_resource_type.get("Server", 0)],
            ],
            "type": "donut",
            "colors": {
                cluster_label: "#6da04b",
                storage_label: "#ffc72c",
                cloud_label: "#2f9fd0",
                server_label: "#e56a54",
            },
        }
    else:
        resource_plot_data = {"type": "donut", "columns": []}

    return resource_plot_data


def generate_allocations_chart_data():
    active_count = Allocation.objects.filter(status__name="Active").count()
    new_count = Allocation.objects.filter(status__name="New").count()
    renewal_requested_count = Allocation.objects.filter(status__name="Renewal Requested").count()

    now = datetime.datetime.now()
    start_time = datetime.date(now.year - 1, 1, 1)
    expired_count = Allocation.objects.filter(status__name="Expired", end_date__gte=start_time).count()

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
        "type": "donut",
        "colors": {
            active_label: "#6da04b",
            new_label: "#2f9fd0",
            renewal_requested_label: "#ffc72c",
            expired_label: "#e56a54",
        },
    }

    return allocation_chart_data
