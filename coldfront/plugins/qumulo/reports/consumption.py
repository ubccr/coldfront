import csv

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from django.db.models import Avg, Max, Min, StdDev, Variance, Count
from django.db.models.expressions import OuterRef, Star, Subquery
from django.db.models.query import QuerySet

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeUsage,
)


def report_boundary_month_dates(report_datetime: datetime) -> tuple:
    previous_month_end_date = (
        report_datetime.replace(day=1) - relativedelta(days=1)
    ).date()
    previous_month_begin_date = previous_month_end_date.replace(day=1)
    return previous_month_begin_date, previous_month_end_date


def get_header() -> list:
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


def generate_row(
    storage_filesystem_path: str, usages: QuerySet[AllocationAttributeUsage]
) -> dict:
    stats = usages.aggregate(
        days=Count(Star()),
        maximum=Max("value"),
        minimum=Min("value"),
        average=Avg("value"),
        standard_deviation=StdDev("value"),
        variance=Variance("value"),
    )
    first_date_entry = usages.last()
    usage_first_date = first_date_entry["value"]
    first_date_to_report = first_date_entry["history_date"].date()
    usage_last_date = usages.first()["value"]
    row = {}
    row["storage_filesystem_path"] = storage_filesystem_path
    row["first_date"] = first_date_to_report
    row["first_date_usage"] = usage_first_date
    row["last_date_usage"] = usage_last_date
    row["difference"] = round(usage_last_date - usage_first_date, 2)
    row |= stats
    return row


def generate_comsumption_usage_report_for(
    begin_date: date,
    end_date: date,
) -> list:
    storage_filesystem_path_sub_query = Subquery(
        AllocationAttribute.objects.filter(
            allocation=OuterRef("pk"),
            allocation_attribute_type__name="storage_filesystem_path",
        ).values("value")
    )
    active_allocations = (
        Allocation.objects.parent()
        .active_storage()
        .consumption()
        .values("id")
        .annotate(storage_filesystem_path=storage_filesystem_path_sub_query)
        .order_by("storage_filesystem_path")
    )
    report = []
    for allocation in active_allocations:
        usages = AllocationAttributeUsage.history.filter(
            allocation_attribute__allocation=allocation["id"],
            allocation_attribute__allocation_attribute_type__name="storage_quota",
            history_date__date__range=(
                begin_date,
                end_date,
            ),
        ).values("value", "history_date__date")
        if not usages:
            continue
        report.append(generate_row(allocation["storage_filesystem_path"], usages))
    return report


def main() -> None:
    month = input(
        "Enter month, \n1 for January, 12 for December and so on \n(defaults to the previous month):"
    )
    if month:
        year = int("Enter year (YYYY): ")
        report_datetime = datetime(year, int(month), 1) + relativedelta(months=1)
    else:
        report_datetime = datetime.now()

    begin_date, end_date = report_boundary_month_dates(report_datetime)
    report = generate_comsumption_usage_report_for(begin_date, end_date)

    file_name_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(f"usage_stats_{file_name_suffix}.csv", "w", newline="\n") as file:
        fieldnames = get_header()
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report)


if __name__ == "__main__":
    main()
