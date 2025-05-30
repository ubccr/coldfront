import csv

from datetime import datetime
from dateutil import relativedelta

from django.db.models import Avg, Max, Min, StdDev, Variance, Count
from django.db.models.expressions import Star

from coldfront.core.allocation.models import (
    AllocationAttributeUsage,
    Allocation,
    AllocationAttribute,
)


def report_boundary_month_dates(report_datetime: datetime) -> tuple:
    previous_month_end_date = (
        report_datetime.replace(day=1) - relativedelta(days=1)
    ).date()
    previous_month_begin_date = previous_month_end_date.replace(day=1)
    return previous_month_begin_date, previous_month_end_date


def get_header() -> str:
    return [
        "storage_filesystem_path",
        "first_date",
        "days",
        "first_date_usage",
        "last_date_usage",
        "difference",
        "maximum",
        "minimum",
        "average",
        "standard_deviation",
        "variance",
    ]


def generate_row(storage_filesystem_path, usages) -> str:
    stats = usages.aggregate(
        days=Count(Star()),
        usage_max=Max("value"),
        usage_min=Min("value"),
        usage_avg=Avg("value"),
        usage_stddev=StdDev("value"),
        usage_variance=Variance("value"),
    )
    first_date_entry = usages.last()
    usage_first_date = first_date_entry["value"]
    first_date_to_report = first_date_entry["history_date"]
    usage_last_date = usages.first()["value"]
    row = {}
    row["storage_filesystem_path"] = storage_filesystem_path
    row["first_date_to_report"] = first_date_to_report
    row["usage_first_date"] = usage_first_date
    row["usage_last_date"] = usage_last_date
    row["difference"] = round(usage_last_date - usage_first_date, 2)
    row |= stats
    return row


def generate_comsumption_usage_report_for(
    begin_date: datetime,
    end_date: datetime,
) -> str:
    active_allocations = Allocation.objects.filter(
        parent_links=None,
        allocationattribute__allocation_attribute_type__name="service_rate",
        allocationattribute__value="consumption",
        resources__name="Storage2",
        status__name="Active",
    )
    report = []
    for allocation in active_allocations:
        usages = AllocationAttributeUsage.history.filter(
            allocation_attribute__allocation=allocation,
            allocation_attribute__allocation_attribute_type__name="storage_quota",
            history_date__date__range=(
                begin_date,
                end_date,
            ),
        ).values("value", "history_date")
        if not usages:
            continue
        storage_filesystem_path = AllocationAttribute.objects.get(
            allocation=allocation,
            allocation_attribute_type__name="storage_filesystem_path",
        ).value
        report.append(generate_row(storage_filesystem_path, usages))
    return report


def main() -> None:

    month = int(
        input(
            "Enter month, \n1 for January, 12 for December and so on \n(defaults to the previous month):"
        )
    )

    if month:
        year = int("Enter year (YYYY): ")
        report_date = datetime(year, month, 1) + relativedelta(months=1)
    else:
        report_date = datetime.now()

    begin_date, end_date = report_boundary_month_dates(report_date)
    print(generate_comsumption_usage_report_for(begin_date, end_date))


if __name__ == "__main__":
    main()
