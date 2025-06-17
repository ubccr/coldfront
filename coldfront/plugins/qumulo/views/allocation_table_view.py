from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, Paginator
from django.db.models.query import QuerySet
from django.views.generic import ListView

from coldfront.plugins.qumulo.forms.AllocationTableSearchForm import (
    AllocationTableSearchForm,
)

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationLinkage,
)
from coldfront.core.resource.models import Resource

from django.db.models import OuterRef, Subquery

from collections import defaultdict


class AllocationListItem:
    id: int
    project_id: int
    project_name: str
    resource_name: str
    department_number: str
    allocation_status: str
    pi_last_name: str
    pi_first_name: str
    pi_user_name: str
    itsd_ticket: str
    file_path: str
    service_rate: str
    child_allocation_ids: List[str]
    is_child: bool

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class AllocationTableView(LoginRequiredMixin, ListView):

    model = Allocation
    template_name = "allocation_table_view.html"
    context_object_name = "allocation_list"
    paginate_by = 25

    def get_queryset(self):

        order_by = self.request.GET.get("order_by")
        if order_by:
            direction = self.request.GET.get("direction")
            dir_dict = {"asc": "", "des": "-"}
            order_by = dir_dict[direction] + order_by
        else:
            order_by = "id"

        view_list: List[AllocationListItem] = []

        allocation_search_form = AllocationTableSearchForm(self.request.GET)

        if allocation_search_form.is_valid():
            data = allocation_search_form.cleaned_data
            resource = Resource.objects.get(name="Storage2")
            allocations = Allocation.objects.filter(resources=resource)

            # find type objects
            department_type = AllocationAttributeType.objects.get(
                name="department_number"
            )

            itsd_ticket_type = AllocationAttributeType.objects.get(
                name="storage_ticket"
            )

            file_path_type = AllocationAttributeType.objects.get(
                name="storage_filesystem_path"
            )

            storage_name_type = AllocationAttributeType.objects.get(
                name="storage_name"
            )

            service_rate_type = AllocationAttributeType.objects.get(name="service_rate")

            # add sub-queries
            department_sub_q = AllocationAttribute.objects.filter(
                allocation=OuterRef("pk"), allocation_attribute_type=department_type
            ).values("value")[:1]

            itsd_ticket_sub_q = AllocationAttribute.objects.filter(
                allocation=OuterRef("pk"), allocation_attribute_type=itsd_ticket_type
            ).values("value")[:1]

            file_path_sub_q = AllocationAttribute.objects.filter(
                allocation=OuterRef("pk"), allocation_attribute_type=file_path_type
            ).values("value")[:1]

            service_rate_sub_q = AllocationAttribute.objects.filter(
                allocation=OuterRef("pk"), allocation_attribute_type=service_rate_type
            ).values("value")[:1]

            storage_name_sub_q = AllocationAttribute.objects.filter(
                allocation=OuterRef("pk"), allocation_attribute_type=storage_name_type
            ).values("value")[:1]

            allocations = allocations.annotate(
                department_number=Subquery(department_sub_q),
                itsd_ticket=Subquery(itsd_ticket_sub_q),
                file_path=Subquery(file_path_sub_q),
                service_rate=Subquery(service_rate_sub_q),
                name=Subquery(storage_name_sub_q),
            )

            # add filters
            if data.get("project_name"):
                allocations = allocations.filter(
                    project__title__icontains=data.get("project_name")
                )

            if data.get("pi_last_name"):
                allocations = allocations.filter(
                    project__pi__last_name__icontains=data.get("pi_last_name")
                )

            if data.get("pi_first_name"):
                allocations = allocations.filter(
                    project__pi__first_name__icontains=data.get("pi_first_name")
                )
            
            if data.get("pi_user_name"):
                allocations = allocations.filter(
                    project__pi__username__icontains=data.get("pi_user_name")
                )

            if data.get("status"):
                allocations = allocations.filter(status__in=data.get("status"))

            if data.get("department_number"):
                allocations = allocations.filter(
                    department_number=data.get("department_number")
                )

            if data.get("itsd_ticket"):
                allocations = allocations.filter(itsd_ticket=data.get("itsd_ticket"))
            
            if data.get("allocation_name"):
                allocations = allocations.filter(name__icontains=data.get("allocation_name"))

            # for now, use a "brute force" approach to
            # group child allocs with parents
            # since there's no DB-agnostic way
            # of pushing this into the query
            allocations = allocations.distinct().order_by(order_by)

            allocation_linkages = AllocationLinkage.objects.filter(
                parent__in=allocations
            )

            parent_to_children_map = defaultdict(list)

            all_allocations = dict()

            for allocation in allocations:
                all_allocations[str(allocation.pk)] = allocation

            all_children = set()

            for linkage in allocation_linkages:
                linkage_children = linkage.children.all().annotate(
                    department_number=Subquery(department_sub_q),
                    itsd_ticket=Subquery(itsd_ticket_sub_q),
                    file_path=Subquery(file_path_sub_q),
                    service_rate=Subquery(service_rate_sub_q),
                )
                linkage_children = linkage_children.order_by(order_by)
                children = [str(child.id) for child in linkage_children]
                all_children.update(children)
                parent_to_children_map[linkage.parent.id] = children

            for allocation in allocations:
                if not data.get("no_grouping", False):
                    if str(allocation.pk) not in all_children:
                        # append a new item, plus any children
                        view_list.append(
                            AllocationListItem(
                                id=allocation.pk,
                                pi_last_name=allocation.project.pi.last_name,
                                pi_first_name=allocation.project.pi.first_name,
                                pi_user_name=allocation.project.pi.username,
                                project_id=allocation.project.pk,
                                project_name=allocation.project.title,
                                resource_name=resource.name,
                                allocation_status=allocation.status.name,
                                department_number=allocation.department_number,
                                itsd_ticket=allocation.itsd_ticket,
                                file_path=allocation.file_path,
                                service_rate=allocation.service_rate,
                                child_allocation_ids=parent_to_children_map[
                                    allocation.id
                                ],
                                is_child=False,
                            )
                        )
                        for child_id in parent_to_children_map[allocation.id]:
                            child_allocation = all_allocations.get(child_id, None)
                            # if child doesn't match filter, then we won't have retrieved it
                            if child_allocation:
                                view_list.append(
                                    AllocationListItem(
                                        id=child_allocation.pk,
                                        pi_last_name=child_allocation.project.pi.last_name,
                                        pi_first_name=child_allocation.project.pi.first_name,
                                        pi_user_name=child_allocation.project.pi.username,
                                        project_id=child_allocation.project.pk,
                                        project_name=child_allocation.project.title,
                                        resource_name=resource.name,
                                        allocation_status=child_allocation.status.name,
                                        department_number=child_allocation.department_number,
                                        itsd_ticket=child_allocation.itsd_ticket,
                                        file_path=child_allocation.file_path,
                                        service_rate=child_allocation.service_rate,
                                        child_allocation_ids=[],
                                        is_child=True,
                                    )
                                )
                else:
                    view_list.append(
                        AllocationListItem(
                            id=allocation.pk,
                            pi_last_name=allocation.project.pi.last_name,
                            pi_first_name=allocation.project.pi.first_name,
                            pi_user_name=allocation.project.pi.username,
                            project_id=allocation.project.pk,
                            project_name=allocation.project.title,
                            resource_name=resource.name,
                            allocation_status=allocation.status.name,
                            department_number=allocation.department_number,
                            itsd_ticket=allocation.itsd_ticket,
                            file_path=allocation.file_path,
                            service_rate=allocation.service_rate,
                            child_allocation_ids=parent_to_children_map[allocation.id],
                            is_child=(str(allocation.pk) in all_children),
                        )
                    )

        return view_list

    def _handle_pagination(
        self, allocation_list: List[AllocationListItem], page_num, page_size
    ):
        paginator = Paginator(allocation_list, page_size)

        try:
            next_page = paginator.page(page_num)
        except EmptyPage:
            next_page = paginator.page(paginator.num_pages)

        return next_page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context["allocation_list"] = self.get_queryset()
        allocations_count = len(self.get_queryset())
        context["allocations_count"] = allocations_count

        allocation_search_form = AllocationTableSearchForm(self.request.GET)

        if allocation_search_form.is_valid():
            data = allocation_search_form.cleaned_data
            filter_parameters = ""
            for key, value in data.items():
                if value:
                    if isinstance(value, QuerySet):
                        filter_parameters += "".join(
                            [f"{key}={ele.pk}&" for ele in value]
                        )
                    elif hasattr(value, "pk"):
                        filter_parameters += f"{key}={value.pk}&"
                    else:
                        filter_parameters += f"{key}={value}&"
            context["allocation_search_form"] = allocation_search_form
        else:
            filter_parameters = None
            context["allocation_search_form"] = AllocationTableSearchForm()

        order_by = self.request.GET.get("order_by")
        if order_by:
            direction = self.request.GET.get("direction")
            filter_parameters_with_order_by = (
                filter_parameters + "order_by=%s&direction=%s&" % (order_by, direction)
            )
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context["expand_accordion"] = "show"
        context["filter_parameters"] = filter_parameters
        context["filter_parameters_with_order_by"] = filter_parameters_with_order_by

        allocation_list = context.get("allocation_list")

        page_num = self.request.GET.get("page")
        if page_num is None or type(page_num) is not int:
            page_num = 1

        allocation_list = self._handle_pagination(
            allocation_list, page_num, self.paginate_by
        )

        return context
