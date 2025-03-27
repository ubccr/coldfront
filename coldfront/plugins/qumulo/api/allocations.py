from typing import Tuple

from django.http import JsonResponse, HttpRequest, HttpResponseBadRequest
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import model_to_dict
from django.db.models import OuterRef, QuerySet, Q
from django.core.exceptions import FieldError

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
)


class Allocations(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 100))
        start_index = (page - 1) * limit
        stop_index = start_index + limit
        sort = request.GET.get("sort", "id")

        allocations_queryset = Allocation.objects.filter(resources__name="Storage2")
        try:
            search = request.GET.getlist("search[]", [])

            for search_param in search:
                if len(search_param.split(":")) != 2:
                    return HttpResponseBadRequest("Invalid search parameter")

                key, value = search_param.split(":")

                if key.startswith("attributes__"):
                    key = key.replace("attributes__", "")
                    query = Q(allocationattribute__allocation_attribute_type__name=key)
                    query &= Q(allocationattribute__value__icontains=value)

                    allocations_queryset = allocations_queryset.filter(query)
                else:
                    allocations_queryset = allocations_queryset.filter(
                        **{f"{key}__icontains": value}
                    )

            if sort.removeprefix("-").startswith("attributes__"):
                (sort, allocations_queryset) = self._handle_attribute_sort(
                    request, allocations_queryset
                )

            total_count = allocations_queryset.count()
            total_pages = -(
                total_count // -limit
            )  # Equivalent to ceil(total_count / limit)

            allocations_queryset = allocations_queryset.order_by(sort)[
                start_index:stop_index
            ]

        except FieldError:
            return HttpResponseBadRequest("Invalid sort key")

        allocations_dicts = list(
            map(
                self._sanitize_allocation,
                allocations_queryset,
            )
        )

        return JsonResponse(
            {"totalPages": total_pages, "allocations": allocations_dicts}
        )

    def _handle_attribute_sort(
        self, request: HttpRequest, allocations_queryset: QuerySet
    ) -> Tuple[str, QuerySet]:
        raw_sort = request.GET.get("sort")
        sort_key = raw_sort.removeprefix("-").removeprefix("attributes__")

        attr = "selected_attr"
        if raw_sort.startswith("-"):
            attr = "-selected_attr"

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=OuterRef("id"),
            allocation_attribute_type__name=sort_key,
        ).values("value")

        allocations_queryset = allocations_queryset.annotate(
            selected_attr=allocation_attributes
        )

        return (attr, allocations_queryset)

    def _sanitize_allocation(self, allocation: Allocation):
        allocation_dict = model_to_dict(allocation)

        allocation_dict["resources"] = list(
            map(lambda resource: resource.name, allocation_dict["resources"])
        )

        allocation_dict["status"] = allocation.status.name

        allocation_attributes = list(
            AllocationAttribute.objects.filter(allocation=allocation)
        )
        allocation_dict["attributes"] = dict()

        for attribute in allocation_attributes:
            allocation_dict["attributes"][
                attribute.allocation_attribute_type.name
            ] = attribute.value

        return allocation_dict
