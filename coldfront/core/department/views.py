"""Department views"""

from django.db.models import Count, Sum, Q, Value, F, When, Case, FloatField
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, ListView
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from ifxuser.models import Organization, OrgRelation, UserAffiliation
from coldfront.core.utils.fasrc import get_resource_rate
from coldfront.core.allocation.models import (Allocation, AllocationUser,
                                            AllocationAttribute)
from coldfront.core.department.forms import DepartmentSearchForm
from coldfront.core.department.models import Department, DepartmentMember


def return_department_roles(user, department):
    """Return list of a user's permissions for the specified department.
    possible roles are: manager, pi, or member.
    """
    member_conditions = (Q(active=1) & Q(user=user))
    if not department.useraffiliation_set.filter(member_conditions).exists():
        return ()

    permissions = ["user"]
    for role in ['approver', 'pi', 'lab_manager']:
        if department.members.filter(
                    member_conditions & Q(role=role)).exists():
            permissions.append(role)

    return permissions

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'department/department_list.html'
    context_object_name = 'department_list'
    paginate_by = 25


    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            direction = '' if direction == 'asc' else '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        department_search_form = DepartmentSearchForm(self.request.GET)
        departments = Department.objects.all()# values()
        user_depts = DepartmentMember.objects.filter(user=self.request.user )
        if department_search_form.is_valid():
            data = department_search_form.cleaned_data
            if not data.get('show_all_departments') or not (self.request.user.is_superuser or
                    self.request.user.has_perm('department.can_view_all_departments')):
                departments = departments.filter(id__in=user_depts.values_list("organization_id"))
            # Department and Rank filters name
            for search in ('name', 'rank'):
                if data.get(search):
                    departments = departments.filter(name__icontains=data.get(search))
        else:
            departments = departments.filter(id__in=user_depts.values_list("organization_id"))

        departments = departments.order_by(order_by).distinct()

        return departments


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        departments_count = self.get_queryset().count()
        context['departments_count'] = departments_count

        department_search_form = DepartmentSearchForm(self.request.GET)
        if department_search_form.is_valid():
            data = department_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        filter_parameters += "".join([f'{key}={ele}&' for ele in value])
                    else:
                        filter_parameters += f'{key}={value}&'
            context['department_search_form'] = department_search_form
        else:
            filter_parameters = None
            context['department_search_form'] = DepartmentSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                f'order_by={order_by}&direction={direction}&'
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        department_list = context.get('department_list')
        paginator = Paginator(department_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            department_list = paginator.page(page)
        except PageNotAnInteger:
            department_list = paginator.page(1)
        except EmptyPage:
            department_list = paginator.page(paginator.num_pages)
        context['department_list'] = department_list

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




class DepartmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Department Stats, Projects, Allocations, and invoice details.
    """
    # should a user need to be a member of the department to see this?
    model = Department
    template_name = "department/department_detail.html"
    context_object_name = 'department'


    def test_func(self):
        """ UserPassesTestMixin Tests.
        Allow access if a department member with billing permission.
        """
        if self.request.user.is_superuser:
            return True
        pk = self.kwargs.get('pk')
        department_obj = get_object_or_404(Department, pk=pk)
        if department_obj.members.filter(user=self.request.user).exists():
            return True

        messages.error(
            self.request, 'You do not have permission to view this department.')
        return False


    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        # Can the user update the department?
        department_obj = self.object
        member_permissions = return_department_roles(self.request.user, department_obj)

        if self.request.user.is_superuser or 'approver' in member_permissions:
            context['manager'] = True
            projectview_filter = Q()
        else:
            context['manager'] = False
            projectview_filter = Q(projectuser__user=self.request.user)

        project_objs = list(department_obj.projects.filter(projectview_filter)\
                    .annotate(total_quota=Sum('allocation__allocationattribute__value', filter=(
                        Q(allocation__allocationattribute__allocation_attribute_type_id=1))&(
                        Q(allocation__status_id=1)))))
        child_depts = Department.objects.filter(parents=department_obj)
        if child_depts:
            for dept in child_depts:
                child_projs = list(dept.projects.filter(projectview_filter)\
                    .annotate(total_quota=Sum('allocation__allocationattribute__value', filter=(
                        Q(allocation__allocationattribute__allocation_attribute_type_id=1))&(
                        Q(allocation__status_id=1)))))
                project_objs.extend(child_projs)

        allocationuser_filter = (Q(status__name='Active') &
                                ~Q(status__name__in=['Removed']) &
                                ~Q(usage_bytes__isnull=True))

        for p in project_objs:
            p.allocs = p.allocation_set.all().\
                    filter(allocationattribute__allocation_attribute_type_id=1).\
                    values('resources__name', 'resources','allocationattribute__value','id').\
                    annotate(size=Sum('allocationattribute__value', filter=(
                        Q(allocationattribute__allocation_attribute_type_id=1))))
            for allocation in p.allocs:
                allocation['price'] = get_resource_rate(allocation['resources__name'])
                allocation['cost'] = allocation['price'] * int(allocation['size']) if allocation['size'] else 0
                allocation['user_count'] = Allocation.objects.get(pk=allocation['id']
                            ).allocationuser_set.filter(allocationuser_filter).count()
                attr_filter = ( Q(allocation_id=allocation['id']) &
                                Q(allocation_attribute_type_id=8))
                if AllocationAttribute.objects.filter(attr_filter):
                    allocation['path'] = AllocationAttribute.objects.get(attr_filter).value
                else:
                    allocation['path'] = ""

            p.total_price = sum(float(a['cost']) for a in p.allocs)

        context['full_price'] = sum(p.total_price for p in project_objs)
        context['projects'] = project_objs
        context['department'] = department_obj

        allocation_objs = Allocation.objects.filter(project_id__in=[o.id for o in project_objs])

        context['allocations_count'] = allocation_objs.count()

        allocation_users = AllocationUser.objects\
                .filter(Q(allocation_id__in=[o.id for o in allocation_objs]) &
                        allocationuser_filter)\
                .order_by('user__username')

        context['allocation_users'] = allocation_users

        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass
        return context


    def post(self, request, *args, **kwargs):
        """activated if the Department is updated"""
        pk = self.kwargs.get('pk')
        # initial_data = {
        #     'status': self.department.status,
        # }
        # form = AllocationInvoiceUpdateForm(
        #     request.POST, initial=initial_data)
        #
        # if form.is_valid():
        #     form_data = form.cleaned_data
        #     allocation_obj.status = form_data.get('status')
        #     allocation_obj.save()
        #     messages.success(request, 'Department updated!')
        # else:
        #     for error in form.errors:
        #         messages.error(request, error)
        return HttpResponseRedirect(reverse('department-detail', kwargs={'pk': pk}))
