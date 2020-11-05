from decimal import Decimal
from django.db.models import Sum
from rest_framework import pagination


class JobPagination(pagination.PageNumberPagination):
    """A PageNumberPagination including aggregate fields over the entire
    Job queryset. Adapted from: https://stackoverflow.com/a/39952895."""

    def paginate_queryset(self, queryset, request, view=None):
        total_amount = queryset.aggregate(
            total_amount=Sum("amount"))["total_amount"]
        if total_amount is None:
            self.total_amount = Decimal("0.00")
        else:
            self.total_amount = total_amount
        total_cpu_time = queryset.aggregate(
            total_cpu_time=Sum("cpu_time"))["total_cpu_time"]
        if total_cpu_time is None:
            self.total_cpu_time = 0.0
        else:
            self.total_cpu_time = total_cpu_time
        return super(JobPagination, self).paginate_queryset(
            queryset, request, view)

    def get_paginated_response(self, data):
        paginated_response = super(JobPagination, self).get_paginated_response(
            data)
        paginated_response.data["total_amount"] = self.total_amount
        paginated_response.data["total_cpu_time"] = self.total_cpu_time
        return paginated_response
