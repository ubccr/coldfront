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
from coldfront.core.allocation.models import Allocation
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
        context = super().get_context_data(**kwargs)
        # Can the user update the department?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_department'] = True
        elif self.object.departmentmember_set.filter(member=self.request.user).exists():
            department_member = self.object.departmentmember_set.get(
                member=self.request.user)
            if department_member.role.name == 'Manager':
                context['is_allowed_to_update_department'] = True
            else:
                context['is_allowed_to_update_department'] = False
        else:
            context['is_allowed_to_update_department'] = False

        # Only show 'Active Users'
        departmentmembers = self.object.departmentmember_set.filter(
            status__name='Active').order_by('user__username')

        if self.request.user.is_superuser or self.request.user.has_perm(
                                        'allocation.can_view_all_allocations'):
            allocations = Allocation.objects.prefetch_related(
                'resources').filter(project=self.object).order_by('-end_date')
        else:
            if self.object.status.name in ['Active', 'New', ]:
                allocations = Allocation.objects.filter(
                    Q(project=self.object) &
                    Q(project__projectuser__user=self.request.user) &
                    Q(project__projectuser__status__name__in=['Active', ]) &
                    Q(status__name__in=['Active', 'Inactive','Paid',
                    'Ready for Review','Payment Requested', ]) &
                    Q(allocationuser__user=self.request.user) &
                    Q(allocationuser__status__name__in=['Active', ])
                ).distinct().order_by('-end_date')
            else:
                allocations = Allocation.objects.prefetch_related(
                    'resources').filter(project=self.object)

        context['allocations'] = allocations
        context['project_users'] = project_users

        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass

        return context


    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        context = self.get_context_data()
        return render(request, self.template_name, context)
