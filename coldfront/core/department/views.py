"""Department views"""

from django.db.models import Count, Sum, Q, Value, F, When, Case, FloatField
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, ListView
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings

from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation,AllocationUser, AllocationUserNote
from coldfront.core.department.forms import DepartmentSearchForm
from coldfront.core.department.models import (Department, DepartmentMemberRole,
                                            DepartmentMemberStatus, DepartmentMember)


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
        departments = Department.objects.prefetch_related('projects')
        user_filter = ( Q(departmentmember__member=self.request.user) &
                        Q(departmentmember__status__name='Active'))

        if department_search_form.is_valid():
            data = department_search_form.cleaned_data
            if data.get('show_all_departments') and (self.request.user.is_superuser or
                    self.request.user.has_perm('department.can_view_all_departments')):
                departments = departments.all()
            else:
                departments = departments.filter(user_filter)
            # Department and Rank filters name
            for search in ('name', 'rank'):
                if data.get(search):
                    departments = departments.filter(name__icontains=data.get(search))
        else:
            departments = departments.filter(user_filter)

        return departments.order_by(order_by).distinct()


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
                        filter_parameters += '{}={}&'.format(key, value)
            context['department_search_form'] = department_search_form
        else:
            filter_parameters = None
            context['department_search_form'] = DepartmentSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                'order_by=%s&direction=%s&' % (order_by, direction)
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





# class DepartmentAllocationInvoiceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
#
#     def get_context_data(self, **kwargs):
#         """Create all the variables for allocation_invoice_detail.html"""
#         pk = self.kwargs.get('pk')
#         department_obj = get_object_or_404(FieldOfScience, pk=pk)
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
    """
    """
    # should a user need to be a member of the department to see this?
    model = Department
    template_name = "department/department_detail.html"
    context_object_name = 'department_detail'


    def test_func(self):
        """ UserPassesTestMixin Tests.
        Allow access if a department member with billing permission.
        """
        if self.request.user.is_superuser:
            return True
        if self.request.user.has_perm('department.can_manage_invoices'):
            return True

        messages.error(
            self.request, 'You do not have permission to manage invoices.')
        return False


    def get_context_data(self, **kwargs):
        # context = super().get_context_data(**kwargs)
        context = {}
        pk = self.kwargs.get('pk')
        department_obj = get_object_or_404(Department, pk=pk)
        # Can the user update the department?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_department'] = True
        elif department_obj.departmentmember_set.filter(member=self.request.user).exists():
            department_member = department_obj.departmentmember_set.get(
                member=self.request.user)
            if department_member.role.name == 'Manager':
                context['is_allowed_to_update_department'] = True
            else:
                context['is_allowed_to_update_department'] = False
        else:
            context['is_allowed_to_update_department'] = False


        project_objs = department_obj.projects.all()\
                    .annotate(total_quota=Sum('allocation__allocationattribute__value', filter=(
                                Q(allocation__allocationattribute__allocation_attribute_type_id=1))\
                                &(Q(allocation__status_id=1))))#\

        price_dict = {1:4.16, 17:20.80, 8:20.80, 7:.41, 2:4.16 }

        whens = [When(resources=k, then=Value(v)) for k, v in price_dict.items()]

        for p in project_objs:
            p.allocations = p.allocation_set.all().\
                    filter(allocationattribute__allocation_attribute_type_id=1).\
                    values('resources__name', 'resources','allocationattribute__value','id').\
                    annotate(price=Case(*whens, output_field=FloatField(), default=Value(0))).\
                    annotate(cost=Sum(F('price')*F('allocationattribute__value'), output_field=FloatField()))

            p.total_price = sum(float(a['allocationattribute__value']) * price_dict[a['resources']] for a in p.allocations)



        context['full_price'] = sum(p.total_price for p in project_objs)
        context['projects'] = project_objs

        allocation_objs = Allocation.objects.filter(project_id__in=[o.id for o in project_objs])

        if self.request.user.is_superuser:
            notes = allocation_objs.first().allocationusernote_set.all()
        else:
            notes = allocation_objs.first().allocationusernote_set.filter(is_private=False)

        context['notes'] = notes
        context['department'] = department_obj

        context['allocations'] = allocation_objs

        allocation_users = AllocationUser.objects.filter(allocation_id__in=[o.id for o in allocation_objs]).filter(status_id=1)\
                .exclude(
            status__name__in=['Removed']).exclude(usage_bytes__isnull=True).order_by('user__username')


        # context['is_allowed_to_update_project'] = set_proj_update_permissions(
        #                                             allocation_objs.first(), self.request.user)

        # Only show 'Active Users'
        departmentmembers = department_obj.departmentmember_set.filter(
            status__name='Active').order_by('member__full_name')

        context['departmentmembers'] = departmentmembers
        context['allocation_users'] = allocation_users

        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass

        return context


    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)


    def post(self, request, *args, **kwargs):
        """activated if the Department gets updated"""
        pk = self.kwargs.get('pk')
        department_obj = get_object_or_404(Department, pk=pk)

        # initial_data = {
        #     'status': department_obj.status,
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
