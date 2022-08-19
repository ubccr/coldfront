department

from django.db.models import Count, Sum, Q, Value, F, When, Case, FloatField
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, ListView
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation
from coldfront.core.department.forms import DepartmentSearchForm
from coldfront.core.department.models import (Department, DepartmentMemberRole,
                                            DepartmentMemberStatus, DepartmentMember)


class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'department/department_list.html'
    # prefetch_related = ['pi', 'status', 'field_of_science', ]
    context_object_name = 'department_list'
    paginate_by = 25

    # def get_queryset(self):
    #     """Connect Department entries to Allocations via Projects
    #     """
    #
    #     dept_allocations = Department.objects.values(
    #         'id',
    #         'description',
    #         'fos_nsf_abbrev',
    #         'project',
    #         'project__allocation'
    #         ).annotate(project_count=Count('project'))\
    #         .filter(project_count__gt=0)
    #     return dept_allocations



    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            direction = '' if direction == 'asc' else '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        department_search_form = DepartmentSearchForm(self.request.GET)


        if department_search_form.is_valid():
            departments = Department.objects.prefetch_related('head')
            data = department_search_form.cleaned_data
            if data.get('show_all_departments') and (self.request.user.is_superuser or self.request.user.has_perm('department.can_view_all_departments')):
                departments = departments.filter(is_biller=True).order_by(order_by)
            else:
                departments = departments.filter(
                    Q(departmentmember__member=self.request.user) &
                    Q(departmentmember__status__name='Active')
                ).order_by(order_by)

            # Department name
            if data.get('name'):
                departments = departments.filter(name__icontains=data.get('name'))

            # Field of Science
            if data.get('field_of_science'):
                departments = departments.filter(
                    field_of_science__description__icontains=data.get('field_of_science'))


        else:
            departments = Department.objects.prefetch_related('head','department__head',
                    ).filter(
                Q(status__name__in=['New', 'Active', ]) &
                Q(departmentmember__member=self.request.user) &
                Q(departmentmember__status__name='Active')
            ).order_by(order_by)
        # else:
        #     allocations = Allocation.objects.prefetch_related('department', 'department__pi', 'status',).filter(
        #         Q(allocationuser__user=self.request.user) &
        #         Q(allocationuser__status__name='Active')
        #     ).order_by(order_by)

        return departments.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        projects_count = self.get_queryset().count()
        context['departments_count'] = departments_count

        department_search_form = DepartmentSearchForm(self.request.GET)
        if department_search_form.is_valid():
            context['department_search_form'] = department_search_form
            data = department_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
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

        return context




class DepartmentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    """
    # should a person need to be a member of the department to see this?
    model = Department
    template_name = "department/department_list.html"
    prefetch_related = ['department', ]
    context_object_name = 'department_list'
    paginate_by = 25



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



    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            direction = '' if direction == 'asc' else '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        department_search_form = DepartmentSearchForm(self.request.GET)

        if department_search_form.is_valid():
            data = department_search_form.cleaned_data
            # if data.get('show_all_projects') and (self.request.user.is_superuser
            # or self.request.user.has_perm('project.can_view_all_projects')):
            departments = Department.objects.prefetch_related( 'pi',  'status',).filter(
                status__name__in=['New', 'department','Active', ]).order_by(order_by)
            # else:
                # projects = Department.objects.prefetch_related('pi',  'status',).filter(
                #     Q(status__name__in=['New', 'department','Active', ]) &
                #     Q(projectuser__user=self.request.user) &
                #     Q(projectuser__status__name='Active')
                # ).order_by(order_by)

            # Dept name
            if data.get('name'):
                departments = departments.filter(name=data.get('name'))

            # Field of Science
            if data.get('department'):
                departments = departments.filter(
                    department__description__icontains=data.get('department'))

        else:
            departments = Department.objects.prefetch_related('department')#.filter(
            #     Q(status__name__in=['New', 'Active', ]) &
            #     Q(allocationuser__user=self.request.user) &
            #     Q(projectuser__user=self.request.user) &
            #     Q(projectuser__status__name='Active')
            # ).order_by(order_by)

        return departments.distinct()



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
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['department_search_form'] = department_search_form
        else:
            filter_parameters = None
            context['department_search_form'] = DepartmentSearchForm()

        order_by = self.request.GET.get('order_by')

        filter_parameters_with_order_by = filter_parameters

        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                'order_by=%s&direction=%s&' % (order_by, direction)

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

        return context












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
        project_users = self.object.projectuser_set.filter(
            status__name='Active').order_by('user__username')

        context['mailto'] = 'mailto:' + \
            ','.join([user.user.email for user in project_users])

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

        context['publications'] = Publication.objects.filter(
            project=self.object, status='Active').order_by('-year')
        context['research_outputs'] = ResearchOutput.objects.filter(
            project=self.object).order_by('-created')
        context['grants'] = Grant.objects.filter(
            project=self.object, status__name__in=['Active', 'Pending', 'Archived'])
        context['allocations'] = allocations
        context['project_users'] = project_users


        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL

        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass

        return context













    def get_context_data(self, **kwargs):
        """Create all the variables for allocation_invoice_detail.html
        """
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        department_obj = get_object_or_404(Department, pk=pk)
        project_objs = department_obj.project_set.all()\
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
        context['allocations'] = allocation_objs

        allocation_users = AllocationUser.objects.filter(allocation_id__in=[o.id for o in allocation_objs]).filter(status_id=1)\
                .exclude(
            status__name__in=['Removed']).exclude(usage_bytes__isnull=True).order_by('user__username')


        initial_data = {
            'status': allocation_objs.first().status,
        }
        form = AllocationInvoiceUpdateForm(initial=initial_data)
        context['form'] = form

        context['department'] = department_obj

        # Can the user update the project?
        context['is_allowed_to_update_project'] = set_proj_update_permissions(
                                                    allocation_objs.first(), self.request.user)
        context['allocation_users'] = allocation_users

        if self.request.user.is_superuser:
            notes = allocation_objs.first().allocationusernote_set.all()
        else:
            notes = allocation_objs.first().allocationusernote_set.filter(
                is_private=False)

        context['notes'] = notes
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        return context


    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        context = self.get_context_data()
        return render(request, self.template_name, context)


    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        initial_data = {
            'status': allocation_obj.status,
        }
        form = AllocationInvoiceUpdateForm(
            request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            allocation_obj.status = form_data.get('status')
            allocation_obj.save()
            messages.success(request, 'Allocation updated!')
        else:
            for error in form.errors:
                messages.error(request, error)
        return HttpResponseRedirect(reverse('allocation-invoice-detail', kwargs={'pk': pk}))
