"""Department views"""

from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Q
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from coldfront.core.utils.views import ColdfrontListView, NoteCreateView, NoteUpdateView
from coldfront.core.allocation.models import Allocation, AllocationUser, AllocationAttributeType
from coldfront.core.department.forms import DepartmentSearchForm
from coldfront.core.department.models import (
    Department,
    DepartmentMember,
    DepartmentUserNote,
)


def return_department_roles(user, department):
    """Return list of a user's permissions for the specified department.
    possible roles are: manager, pi, or member.
    """
    member_conditions = (Q(active=1) & Q(user=user))
    if not department.useraffiliation_set.filter(member_conditions).exists():
        return ()

    permissions = ['user']
    for role in ['approver', 'pi', 'lab_manager']:
        if department.members.filter(member_conditions & Q(role=role)).exists():
            permissions.append(role)

    return permissions


class DepartmentListView(ColdfrontListView):
    model = Department
    template_name = 'department/department_list.html'
    context_object_name = 'item_list'

    def get_queryset(self):
        order_by = self.return_order()

        department_search_form = DepartmentSearchForm(self.request.GET)
        departments = Department.objects.all()  # values()
        user_depts = DepartmentMember.objects.filter(user=self.request.user)
        if department_search_form.is_valid():
            data = department_search_form.cleaned_data
            if not data.get('show_all_departments') or not (
                self.request.user.is_superuser
                or self.request.user.has_perm('department.can_view_all_departments')
            ):
                departments = departments.filter(
                    id__in=user_depts.values_list('organization_id')
                )
            # Department and Rank filters name
            for search in ('name', 'rank'):
                if data.get(search):
                    departments = departments.filter(name__icontains=data.get(search))
        else:
            departments = departments.filter(
                id__in=user_depts.values_list('organization_id')
            )

        departments = departments.order_by(order_by).distinct()
        return departments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            SearchFormClass=DepartmentSearchForm, **kwargs
        )
        return context


# class DepartmentInvoiceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
#
#     def get_context_data(self, **kwargs):
#         """Create all the variables for allocation_invoice_detail.html"""
#         pk = self.kwargs.get('pk')
#         self.department = get_object_or_404(FieldOfScience, pk=pk)
#
#
#         initial_data = {
#             'status': allocation_objs.first().status,
#         }
#         form = AllocationInvoiceUpdateForm(initial=initial_data)
#         context['form'] = form
#
#         # Can the user update the project?
#         context['is_allowed_to_update_project'] = set_proj_update_permissions(
#                                                     allocation_objs.first(), self.request.user)

#
#         context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
#         return context


class DepartmentNoteCreateView(NoteCreateView):
    model = DepartmentUserNote
    fields = '__all__'
    form_obj = 'department'
    object_model = Department

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_page'] = 'department-detail'
        context['object_title'] = f'Department {context["object"].name}'
        return context

    def get_success_url(self):
        return reverse('department-detail', kwargs={'pk': self.kwargs.get('pk')})


class DepartmentNoteUpdateView(NoteUpdateView):
    model = DepartmentUserNote

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.department
        context['object_detail_link'] = 'department-detail'
        return context

    def get_success_url(self):
        return reverse_lazy('department-detail', kwargs={'pk': self.object.department.pk})


class DepartmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Department Stats, Projects, Allocations, and invoice details."""

    # should a user need to be a member of the department to see this?
    model = Department
    template_name = 'department/department_detail.html'
    context_object_name = 'department'

    def test_func(self):
        """UserPassesTestMixin Tests.
        Allow access if a department member with billing permission.
        """
        if self.request.user.is_superuser:
            return True
        pk = self.kwargs.get('pk')
        department_obj = get_object_or_404(Department, pk=pk)
        if department_obj.members.filter(user=self.request.user).exists():
            return True

        err = 'You do not have permission to view this department.'
        messages.error(self.request, err)
        return False

    def return_visible_notes(self, department_obj):
        noteset = department_obj.departmentusernote_set
        notes = (
            noteset.all()
            if self.request.user.is_superuser
            else noteset.filter(is_private=False)
        )
        return notes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Can the user update the department?
        department_obj = self.object
        member_permissions = return_department_roles(self.request.user, department_obj)

        if self.request.user.is_superuser or 'approver' in member_permissions:
            context['manager'] = True
            projectview_filter = Q(status__name__in=['New', 'Active'])
        else:
            context['manager'] = False
            projectview_filter = Q(
                status__name__in=['New', 'Active'], projectuser__user=self.request.user
            )

        quota_attr_ids = [
            attr.pk for attr in AllocationAttributeType.objects.filter(
                name__in=['Core Usage (Hours)', 'Storage Quota (TB)']
            )
        ]

        attribute_filter = (
            Q(allocation__allocationattribute__allocation_attribute_type_id__in=quota_attr_ids)
            & Q(allocation__status__name='Active')
        )
        attribute_string = 'allocation__allocationattribute__value'
        project_objs = list(
            department_obj.projects.filter(projectview_filter).annotate(
                total_quota=Sum(attribute_string, filter=attribute_filter)
            )
        )

        allocationuser_filter = (Q(status__name='Active') & ~Q(usage_bytes__isnull=True))

        quota_attrs = AllocationAttributeType.objects.filter(
            name__in=['Core Usage (Hours)', 'Storage Quota (TB)']
        )

        storage_pi_dict = {p.pi: [] for p in project_objs}
        compute_pi_dict = {p.pi: [] for p in project_objs}
        for p in project_objs:
            p.allocs = p.allocation_set.filter(
                allocationattribute__allocation_attribute_type__in=quota_attrs,
                status__name='Active',
            )
            p.storage_allocs = p.allocs.filter(
                resources__resource_type__name='Storage')
            p.compute_allocs = p.allocs.filter(
                resources__resource_type__name='Cluster')
            storage_pi_dict[p.pi].extend(list(p.storage_allocs))
            compute_pi_dict[p.pi].extend(list(p.compute_allocs))
        storage_pi_dict = {pi:allocs for pi, allocs in storage_pi_dict.items() if allocs}
        compute_pi_dict = {pi:allocs for pi, allocs in compute_pi_dict.items() if allocs}
        for pi, allocs in storage_pi_dict.items():
            pi.storage_total_price = sum(float(a.cost) for a in allocs)
        for pi, allocs in compute_pi_dict.items():
            pi.compute_total_price = sum(float(a.cost) for a in allocs)

        context['compute_pi_dict'] = compute_pi_dict
        context['storage_pi_dict'] = storage_pi_dict
        context['projects'] = project_objs
        context['department'] = department_obj

        allocation_objs = Allocation.objects.filter(
            project_id__in=[o.id for o in project_objs],
            status__name='Active',
        )

        allocation_users = AllocationUser.objects.filter(
            Q(allocation_id__in=[o.id for o in allocation_objs]) & allocationuser_filter
        ).order_by('user__username')
        context['notes'] = self.return_visible_notes(department_obj)
        context['note_update_link'] = 'department-note-update'

        storage_full_price = sum(pi.storage_total_price for pi in storage_pi_dict.keys())
        # compute_full_price = sum(pi.compute_total_price for pi in compute_pi_dict.keys())
        detail_table = [
            ('Department', department_obj.name),
        ]
        if self.request.user.is_superuser or 'approver' in member_permissions:
            detail_table.extend([
                ('Total Labs in Bill', len(project_objs)),
                ('Total Allocations in Bill', allocation_objs.count()),
                ('Total Users in Bill', allocation_users.count()),
            ])
        else:
            detail_table.extend([
                ('Your Labs', len(project_objs)),
                ('Your Allocations', allocation_objs.count()),
                ('Total Users in Your Allocations', allocation_users.count()),
            ])
        detail_table.extend([
            ('Service Period', '1 Month'),
            ('Total Amount Due, Monthly Storage', f'${round(storage_full_price, 2)}'),
            # ( 'Total Amount Due, Quarterly Compute':f'${round(compute_full_price, 2)}')
        ])
        context['detail_table'] = detail_table

        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass
        return context
