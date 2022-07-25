import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Case, CharField, Q, Value, When
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserAttribute,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import allocation_activate_user
from coldfront.core.allocation.utils import get_allocation_user_cluster_access_status
from coldfront.core.allocation.utils import get_project_compute_allocation
# from coldfront.core.grant.models import Grant
from coldfront.core.allocation.utils_.secure_dir_utils import \
    pi_eligible_to_request_secure_dir
from coldfront.core.project.forms import (ProjectAddUserForm,
                                          ProjectAddUsersToAllocationForm,
                                          ProjectReviewEmailForm,
                                          ProjectReviewForm,
                                          ProjectReviewUserJoinForm,
                                          ProjectSearchForm,
                                          ProjectUpdateForm,
                                          ProjectUserUpdateForm,
                                          JoinRequestSearchForm,
                                          ProjectSelectHostUserForm)
from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectReviewStatusChoice,
                                           ProjectStatusChoice, ProjectUser,
                                           ProjectUserJoinRequest,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice,
                                           SavioProjectAllocationRequest,
                                           VectorProjectAllocationRequest)
from coldfront.core.project.utils import (ProjectClusterAccessRequestRunner,
                                          send_added_to_project_notification_email,
                                          send_project_join_notification_email,
                                          send_project_join_request_approval_email,
                                          send_project_join_request_denial_email)
from coldfront.core.project.utils_.addition_utils import can_project_purchase_service_units
from coldfront.core.project.utils_.new_project_utils import add_vector_user_to_designated_savio_project
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import is_any_project_pi_renewable
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.models import UserProfile
from coldfront.core.user.utils import CombinedUserSearch, is_lbl_employee, \
    needs_host, access_agreement_signed
from coldfront.core.utils.common import (get_domain_url, import_from_settings)
from coldfront.core.utils.mail import send_email, send_email_template

from flags.state import flag_enabled

import logging

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)

if EMAIL_ENABLED:
    EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
        'EMAIL_DIRECTOR_EMAIL_ADDRESS')
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    SUPPORT_EMAIL = import_from_settings('CENTER_HELP_EMAIL')
    EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST')

logger = logging.getLogger(__name__)


class ProjectDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Project
    template_name = 'project/project_detail.html'
    context_object_name = 'project'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_view_all_projects'):
            return True

        project_obj = self.get_object()

        if project_obj.projectuser_set.filter(user=self.request.user, status__name__in=['Active', 'Pending - Remove']).exists():
            return True

        messages.error(
            self.request, 'You do not have permission to view the previous page.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Can the user archive the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_archive_project'] = True
        else:
            context['is_allowed_to_archive_project'] = False

        # Can the user update the project?
        context['is_allowed_to_update_project'] = False
        context['can_leave_project'] = False

        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True

        if self.object.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.projectuser_set.get(user=self.request.user)

            if project_user.role.name in ['Principal Investigator', 'Manager']:
                context['username'] = project_user.user.username
                context['is_allowed_to_update_project'] = True

            if project_user.status.name == 'Active' and project_user.role.name == 'User':
                context['can_leave_project'] = True

            if project_user.role.name == 'Manager' and len(self.object.projectuser_set.filter(role__name='Manager')) > 1:
                context['can_leave_project'] = True

        # Retrieve cluster access statuses.
        cluster_access_statuses = {}
        try:
            allocation_obj = get_project_compute_allocation(self.object)
            statuses = \
                allocation_obj.allocationuserattribute_set.select_related(
                    'allocation_user__user'
                ).filter(
                    allocation_attribute_type__name='Cluster Account Status',
                    value__in=['Pending - Add', 'Processing', 'Active'])
            for status in statuses:
                username = status.allocation_user.user.username
                cluster_access_statuses[username] = status.value
        except (Allocation.DoesNotExist, Allocation.MultipleObjectsReturned):
            pass

        whens = [
            When(user__username=username, then=Value(status))
            for username, status in cluster_access_statuses.items()
        ]

        # Only show 'Active Users'
        project_users = self.object.projectuser_set.select_related(
            'user'
        ).filter(
            status__name='Active'
        ).annotate(
            cluster_access_status=Case(
                *whens,
                default=Value('None'),
                output_field=CharField(),
            )
        ).order_by('user__username')

        context['mailto'] = 'mailto:' + \
            ','.join([user.user.email for user in project_users])

        is_pi = self.object.projectuser_set.filter(
            user=self.request.user,
            role__name='Principal Investigator',
            status__name='Active').exists()

        if self.request.user.is_superuser or self.request.user.has_perm('allocation.can_view_all_allocations') or is_pi:
            allocations = Allocation.objects.prefetch_related(
                'resources').filter(project=self.object).order_by('-end_date')
        else:
            if self.object.status.name in ['Active', 'New', ]:
                allocations = Allocation.objects.filter(
                    Q(project=self.object) &
                    Q(project__projectuser__user=self.request.user) &
                    Q(project__projectuser__status__name__in=['Active', ]) &
                    Q(status__name__in=['Active', 'Expired',
                                        'New', 'Renewal Requested',
                                        'Payment Pending', 'Payment Requested',
                                        'Payment Declined', 'Paid']) &
                    Q(allocationuser__user=self.request.user) &
                    Q(allocationuser__status__name__in=['Active', ])
                ).distinct().order_by('-end_date')
            else:
                allocations = Allocation.objects.prefetch_related(
                    'resources').filter(project=self.object)

        context['num_join_requests'] = self.object.projectuser_set.filter(
            status__name='Pending - Add').count()

        # context['publications'] = Publication.objects.filter(project=self.object, status='Active').order_by('-year')
        # context['research_outputs'] = ResearchOutput.objects.filter(project=self.object).order_by('-created')
        # context['grants'] = Grant.objects.filter(project=self.object, status__name__in=['Active', 'Pending'])
        context['allocations'] = allocations
        context['project_users'] = project_users
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL

        # Can the user request cluster access on own or others' behalf?
        try:
            allocation = get_project_compute_allocation(self.object)
        except Allocation.DoesNotExist:
            compute_allocation_pk = None
            cluster_accounts_requestable = False
            cluster_accounts_tooltip = 'Unexpected server error.'
        except Allocation.MultipleObjectsReturned:
            compute_allocation_pk = None
            cluster_accounts_requestable = False
            cluster_accounts_tooltip = 'Unexpected server error.'
        else:
            compute_allocation_pk = allocation.pk
            cluster_accounts_requestable = True
            if context['is_allowed_to_update_project']:
                cluster_accounts_tooltip = (
                    'Request access to the cluster under this project on '
                    'behalf of users.')
            else:
                cluster_accounts_tooltip = (
                    'Request access to the cluster under this project.')
        context['compute_allocation_pk'] = compute_allocation_pk
        context['cluster_accounts_requestable'] = cluster_accounts_requestable
        context['cluster_accounts_tooltip'] = cluster_accounts_tooltip

        # Display the "Renew Allowance" button for eligible allocation types.
        eligible_project_prefixes = (
            'fc_'
            # TODO: Include these when ready.
            # 'ic_',
            # 'pc_',
        )
        context['renew_allowance_visible'] = self.object.name.startswith(
            eligible_project_prefixes)
        # Only allow the "Renew Allowance" button to be clickable if
        #     (a) any PIs do not have pending/approved renewal requests for the
        #         current period, or
        #     (b) renewals for the next period can be requested.
        # TODO: Set this dynamically when supporting other types.
        allocation_period = get_current_allowance_year_period()
        context['renew_allowance_clickable'] = (
            context['renew_allowance_visible'] and
            is_any_project_pi_renewable(self.object, allocation_period) or
            flag_enabled('ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'))

        # Display the "Purchase Service Units" button for eligible allocation
        # types, for those allowed to update the project.
        context['purchase_sus_visible'] = (
            can_project_purchase_service_units(self.object) and
            context.get('is_allowed_to_update_project', False))

        # Only active PIs of active FCAs, ICAs and Condos can request
        # secure directories
        context['can_request_sec_dir'] = \
            pi_eligible_to_request_secure_dir(self.request.user)

        context['user_agreement_signed'] = \
            access_agreement_signed(self.request.user)

        return context


class ProjectListView(LoginRequiredMixin, ListView):

    model = Project
    template_name = 'project/project_list.html'
    prefetch_related = ['status', 'field_of_science', ]
    context_object_name = 'project_list'
    paginate_by = 25

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        project_search_form = ProjectSearchForm(self.request.GET)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if data.get('show_all_projects') and (self.request.user.is_superuser or self.request.user.has_perm('project.can_view_all_projects')):
                projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                    status__name__in=['New', 'Active', 'Inactive', ]
                ).annotate(
                    cluster_name=Case(
                        When(name='abc', then=Value('ABC')),
                        When(name__startswith='vector_', then=Value('Vector')),
                        default=Value('Savio'),
                        output_field=CharField(),
                    )
                ).order_by(order_by)
            else:
                projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                    Q(status__name__in=['New', 'Active', 'Inactive', ]) &
                    Q(projectuser__user=self.request.user) &
                    Q(projectuser__status__name__in=['Active',  'Pending - Remove'])
                ).annotate(
                    cluster_name=Case(
                        When(name='abc', then=Value('ABC')),
                        When(name__startswith='vector_', then=Value('Vector')),
                        default=Value('Savio'),
                        output_field=CharField(),
                    ),
                ).order_by(order_by)

            # Last Name
            if data.get('last_name'):
                pi_project_users = ProjectUser.objects.filter(
                    project__in=projects,
                    role__name='Principal Investigator',
                    user__last_name__icontains=data.get('last_name'))
                project_ids = pi_project_users.values_list(
                    'project_id', flat=True)
                projects = projects.filter(id__in=project_ids)

            # Username
            if data.get('username'):
                projects = projects.filter(
                    Q(projectuser__user__username__icontains=data.get(
                        'username')) &
                    (Q(projectuser__role__name='Principal Investigator') |
                     Q(projectuser__status__name='Active'))
                )

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get('field_of_science'))

            # Project Title
            if data.get('project_title'):
                projects = projects.filter(title__icontains=data.get('project_title'))

            # Project Name
            if data.get('project_name'):
                projects = projects.filter(name__icontains=data.get('project_name'))

            # Cluster Name
            if data.get('cluster_name'):
                projects = projects.filter(cluster_name__icontains=data.get('cluster_name'))

        else:
            projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                Q(status__name__in=['New', 'Active', 'Inactive', ]) &
                Q(projectuser__user=self.request.user) &
                Q(projectuser__status__name__in=['Active', 'Pending - Remove'])
            ).annotate(
                cluster_name=Case(
                    When(name='abc', then=Value('ABC')),
                    When(name__startswith='vector_', then=Value('Vector')),
                    default=Value('Savio'),
                    output_field=CharField(),
                ),
            ).order_by(order_by)

        return projects.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # block access to joining projects until user-acess-agreement has been signed
        context['user_agreement_signed'] = self.request.user.userprofile.access_agreement_signed_date is not None

        projects_count = self.get_queryset().count()
        context['projects_count'] = projects_count

        project_search_form = ProjectSearchForm(self.request.GET)
        if project_search_form.is_valid():
            context['project_search_form'] = project_search_form
            data = project_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['project_search_form'] = project_search_form
        else:
            filter_parameters = None
            context['project_search_form'] = ProjectSearchForm()

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

        project_list = context.get('project_list')
        paginator = Paginator(project_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            project_list = paginator.page(page)
        except PageNotAnInteger:
            project_list = paginator.page(1)
        except EmptyPage:
            project_list = paginator.page(paginator.num_pages)

        # The "Renew a PI's Allowance" button should only be visible to
        # Managers and PIs.
        role_names = ['Manager', 'Principal Investigator']
        status = ProjectUserStatusChoice.objects.get(name='Active')
        context['renew_allowance_visible'] = \
            ProjectUser.objects.filter(
                user=self.request.user, role__name__in=role_names,
                status=status)

        context['user_agreement_signed'] = \
            access_agreement_signed(self.request.user)

        return context


class ProjectArchivedListView(LoginRequiredMixin, UserPassesTestMixin,
                              ListView):

    model = Project
    template_name = 'project/project_archived_list.html'
    prefetch_related = ['status', 'field_of_science', ]
    context_object_name = 'project_list'
    paginate_by = 10

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        project_search_form = ProjectSearchForm(self.request.GET)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if data.get('show_all_projects') and (self.request.user.is_superuser or self.request.user.has_perm('project.can_view_all_projects')):
                projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                    status__name__in=['Archived', ]).order_by(order_by)
            else:

                projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                    Q(status__name__in=['Archived', ]) &
                    Q(projectuser__user=self.request.user) &
                    Q(projectuser__status__name='Active')
                ).order_by(order_by)

            # Last Name
            if data.get('last_name'):
                pi_project_users = ProjectUser.objects.filter(
                    project__in=projects,
                    role__name='Principal Investigator',
                    user__last_name__icontains=data.get('last_name'))
                project_ids = pi_project_users.values_list(
                    'project_id', flat=True)
                projects = projects.filter(id__in=project_ids)

            # Username
            if data.get('username'):
                projects = projects.filter(
                    projectuser__user__username__icontains=data.get('username'),
                    projectuser__role__name='Principal Investigator')

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get('field_of_science'))

            # Project Title
            if data.get('project_title'):
                projects = projects.filter(title__icontains=data.get('project_title'))

            # Project Name
            if data.get('project_name'):
                projects = projects.filter(name__icontains=data.get('project_name'))

        else:
            projects = Project.objects.prefetch_related('field_of_science', 'status',).filter(
                Q(status__name__in=['Archived', ]) &
                Q(projectuser__user=self.request.user) &
                Q(projectuser__status__name='Active')
            ).order_by(order_by)

        return projects

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        projects_count = self.get_queryset().count()
        context['projects_count'] = projects_count
        context['expand'] = False

        project_search_form = ProjectSearchForm(self.request.GET)
        if project_search_form.is_valid():
            context['project_search_form'] = project_search_form
            data = project_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['project_search_form'] = project_search_form
        else:
            filter_parameters = None
            context['project_search_form'] = ProjectSearchForm()

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

        project_list = context.get('project_list')
        paginator = Paginator(project_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            project_list = paginator.page(page)
        except PageNotAnInteger:
            project_list = paginator.page(1)
        except EmptyPage:
            project_list = paginator.page(paginator.num_pages)

        return context


class ProjectArchiveProjectView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_archive.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.method == 'POST':
            return False

        # project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        #
        # if project_obj.projectuser_set.filter(
        #         user=self.request.user,
        #         role__name__in=['Manager', 'Principal Investigator'],
        #         status__name='Active').exists():
        #     return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project = get_object_or_404(Project, pk=pk)

        context['project'] = project
        context['is_allowed_to_archive_project'] = self.request.user.is_superuser

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project = get_object_or_404(Project, pk=pk)
        project_status_archive = ProjectStatusChoice.objects.get(
            name='Archived')
        allocation_status_expired = AllocationStatusChoice.objects.get(
            name='Expired')
        end_date = datetime.datetime.now()
        project.status = project_status_archive
        project.save()
        for allocation in project.allocation_set.filter(status__name='Active'):
            allocation.status = allocation_status_expired
            allocation.end_date = end_date
            allocation.save()
        return redirect(reverse('project-detail', kwargs={'pk': project.pk}))


class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    template_name_suffix = '_create_form'
    fields = ['title', 'description', 'field_of_science', ]

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        # if self.request.user.userprofile.is_pi:
        #     return True

    def form_valid(self, form):
        project_obj = form.save(commit=False)
        form.instance.status = ProjectStatusChoice.objects.get(name='New')
        project_obj.save()
        self.object = project_obj

        project_user_obj = ProjectUser.objects.create(
            user=self.request.user,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active')
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Project
    template_name_suffix = '_update_form'
    form_class = ProjectUpdateForm
    success_message = 'Project updated.'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = self.get_object()

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot update an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        return super().form_valid(form)


class ProjectAddUsersSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_add_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'Inactive', 'New', ]:
            messages.error(
                request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_search_form'] = UserSearchForm()
        context['project'] = Project.objects.get(pk=self.kwargs.get('pk'))
        return context


class ProjectAddUsersSearchResultsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/add_user_search_results.html'
    raise_exception = True

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'Inactive', 'New', ]:
            messages.error(
                request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(
            status__name__in=['Pending - Add', 'Active'])]

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        matches = context.get('matches')
        for match in matches:

            # add data for access agreements
            match.update(
                {'role': ProjectUserRoleChoice.objects.get(name='User'),
                 'user_access_agreement':
                     'Signed' if User.objects.get(username=match['username']).
                                       userprofile.access_agreement_signed_date
                                 is not None else 'Unsigned'
                 })

        if matches:
            formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
            formset = formset(initial=matches, prefix='userform')

            # cache User objects
            match_users = User.objects.filter(username__in=[form._username for form in formset])
            for form in formset:
                # disable user matches with unsigned signed user agreement
                if not match_users.get(username=form._username).userprofile.access_agreement_signed_date is not None:
                    form.fields.pop('selected')

            context['formset'] = formset
            context['user_search_string'] = user_search_string
            context['search_by'] = search_by

        users_already_in_project = []
        for ele in user_search_string.split():
            if ele in users_to_exclude:
                users_already_in_project.append(ele)
        context['users_already_in_project'] = users_already_in_project

        # The following block of code is used to hide/show the allocation div in the form.
        if project_obj.allocation_set.filter(status__name__in=['Active', 'New', 'Renewal Requested']).exists():
            div_allocation_class = 'placeholder_div_class'
        else:
            div_allocation_class = 'd-none'
        context['div_allocation_class'] = div_allocation_class
        ###

        allocation_form = ProjectAddUsersToAllocationForm(
            request.user, project_obj.pk, prefix='allocationform')
        context['pk'] = pk
        context['allocation_form'] = allocation_form
        return render(request, self.template_name, context)


class ProjectAddUsersView(LoginRequiredMixin, UserPassesTestMixin, View):

    logger = logging.getLogger(__name__)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'Inactive', 'New', ]:
            messages.error(
                request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(
            status__name='Active')]

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        matches = context.get('matches')
        for match in matches:
            match.update(
                {'role': ProjectUserRoleChoice.objects.get(name='User'),
                 'user_access_agreement':
                     'Signed' if User.objects.get(username=match['username']).
                                     userprofile.access_agreement_signed_date
                                 is not None else 'Unsigned'
                 })

        formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
        formset = formset(request.POST, initial=matches, prefix='userform')

        allocation_form = ProjectAddUsersToAllocationForm(
            request.user, project_obj.pk, request.POST, prefix='allocationform')

        added_users_count = 0
        cluster_access_requests_count = 0
        if formset.is_valid() and allocation_form.is_valid():
            project_user_active_status_choice = ProjectUserStatusChoice.objects.get(
                name='Active')
            allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active')
            allocation_form_data = allocation_form.cleaned_data['allocation']
            if '__select_all__' in allocation_form_data:
                allocation_form_data.remove('__select_all__')

            unsigned_users = []
            added_users = []
            for form in formset:
                user_form_data = form.cleaned_data
                # checking for users with pending/processing project removal requests.
                username = user_form_data.get('username')
                pending_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Pending')
                processing_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')

                if ProjectUserRemovalRequest.objects.\
                        filter(project_user__user__username=username,
                               project_user__project=project_obj,
                               status__in=[pending_status, processing_status]).exists():

                    message = (
                        f'A pending request to remove User {username} from '
                        f'Project {project_obj.name} has been made. Please '
                        f'wait until it is completed before adding the user '
                        f'again.')
                    messages.error(request, message)
                    continue

                # recording users with unsigned user access agreements
                if user_form_data['user_access_agreement'] == 'Unsigned':
                    unsigned_users.append(user_form_data['username'])
                    continue

                if user_form_data['selected']:
                    added_users_count += 1
                    added_users.append(user_form_data['username'])

                    # Will create local copy of user if not already present in local database
                    user_obj, _ = User.objects.get_or_create(
                        username=user_form_data.get('username'))
                    user_obj.first_name = user_form_data.get('first_name')
                    user_obj.last_name = user_form_data.get('last_name')
                    user_obj.email = user_form_data.get('email')
                    user_obj.save()

                    role_choice = user_form_data.get('role')
                    # Is the user already in the project?
                    if project_obj.projectuser_set.filter(user=user_obj).exists():
                        project_user_obj = project_obj.projectuser_set.get(
                            user=user_obj)
                        project_user_obj.role = role_choice
                        project_user_obj.status = project_user_active_status_choice
                        project_user_obj.save()
                    else:
                        project_user_obj = ProjectUser.objects.create(
                            user=user_obj, project=project_obj, role=role_choice, status=project_user_active_status_choice)

                    for allocation in Allocation.objects.filter(pk__in=allocation_form_data):
                        if allocation.allocationuser_set.filter(user=user_obj).exists():
                            allocation_user_obj = allocation.allocationuser_set.get(
                                user=user_obj)
                            allocation_user_obj.status = allocation_user_active_status_choice
                            allocation_user_obj.save()
                        else:
                            allocation_user_obj = AllocationUser.objects.create(
                                allocation=allocation,
                                user=user_obj,
                                status=allocation_user_active_status_choice)
                        allocation_activate_user.send(sender=self.__class__,
                                                      allocation_user_pk=allocation_user_obj.pk)

                    # Request cluster access for the user.
                    request_runner = ProjectClusterAccessRequestRunner(
                        project_user_obj)
                    runner_result = request_runner.run()
                    if runner_result.success:
                        cluster_access_requests_count += 1
                    else:
                        messages.error(
                            self.request, runner_result.error_message)

                    # Notify the user that he/she has been added.
                    try:
                        send_added_to_project_notification_email(
                            project_obj, project_user_obj)
                    except Exception as e:
                        message = 'Failed to send notification email. Details:'
                        self.logger.error(message)
                        self.logger.exception(e)

                    # If the Project is a Vector project, automatically add the
                    # User to the designated Savio project for Vector users.
                    if project_obj.name.startswith('vector_'):
                        try:
                            add_vector_user_to_designated_savio_project(
                                user_obj)
                        except Exception as e:
                            message = (
                                f'Encountered unexpected exception when '
                                f'automatically providing User {user_obj.pk} '
                                f'with access to Savio. Details:')
                            self.logger.error(message)
                            self.logger.exception(e)

            # checking if there were any users with unsigned user access agreements in the form
            if unsigned_users:
                unsigned_users_string = ", ".join(unsigned_users)

                # changing grammar for one vs multiple users
                if len(unsigned_users) == 1:
                    message = f'User [{unsigned_users_string}] does not have ' \
                              f'a signed User Access Agreement and was ' \
                              f'therefore not added to the project.'
                else:
                    message = f'Users [{unsigned_users_string}] do not have ' \
                              f'a signed User Access Agreement and were ' \
                              f'therefore not added to the project.'
                messages.error(request, message)

            if added_users_count != 0:
                added_users_string = ", ".join(added_users)
                messages.success(
                    request, 'Added [{}] to project.'.format(added_users_string))

                message = (
                    f'Requested cluster access under project for '
                    f'{cluster_access_requests_count} users.')
                messages.success(request, message)

            else:
                messages.info(request, 'No users selected to add.')

        else:
            if not formset.is_valid():
                for error in formset.errors:
                    messages.error(request, error)

            if not allocation_form.is_valid():
                for error in allocation_form.errors:
                    messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectUserDetail(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_user_detail.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_user_pk = self.kwargs.get('project_user_pk')

        if project_obj.projectuser_set.filter(pk=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(
                pk=project_user_pk)

            project_user_update_form = ProjectUserUpdateForm(
                initial={'role': project_user_obj.role, 'enable_notifications':
                    project_user_obj.enable_notifications})

            context = {}
            context['project_obj'] = project_obj
            context['project_user_update_form'] = project_user_update_form
            context['project_user_obj'] = project_user_obj
            context['project_user_is_manager'] = project_user_obj.role.name == 'Manager'

            try:
                allocation_obj = get_project_compute_allocation(project_obj)
            except (Allocation.DoesNotExist,
                    Allocation.MultipleObjectsReturned):
                allocation_obj = None
                cluster_access_status = 'Error'
            else:
                try:
                    cluster_access_status = \
                        get_allocation_user_cluster_access_status(
                            allocation_obj, project_user_obj.user).value
                except AllocationUserAttribute.DoesNotExist:
                    cluster_access_status = 'None'
                except AllocationUserAttribute.MultipleObjectsReturned:
                    cluster_access_status = 'Error'
            context['allocation_obj'] = allocation_obj
            context['cluster_access_status'] = cluster_access_status

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_user_pk = self.kwargs.get('project_user_pk')

        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot update a user in an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if project_obj.projectuser_set.filter(id=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(pk=project_user_pk)
            managers = project_obj.projectuser_set.filter(role__name='Manager', status__name='Active')
            project_pis = project_obj.projectuser_set.filter(role__name='Principal Investigator', status__name='Active')

            project_user_update_form = ProjectUserUpdateForm(request.POST,
                                                             initial={'role': project_user_obj.role.name,
                                                                      'enable_notifications': project_user_obj.enable_notifications})

            is_request_by_superuser = project_obj.projectuser_set.filter(user=self.request.user,
                                                                         role__name__in=['Manager',
                                                                                         'Principal Investigator'],
                                                                         status__name='Active').exists() or self.request.user.is_superuser

            if project_user_obj.role.name == 'Principal Investigator':
                enable_notifications = project_user_update_form.data.get('enable_notifications', 'off') == 'on'

                # cannot disable when no manager(s) exists
                if not managers.exists() and not enable_notifications:
                    messages.error(request, 'PIs can disable notifications when at least one manager exists.')
                else:
                    project_user_obj.enable_notifications = enable_notifications
                    project_user_obj.save()
                    messages.success(request, 'User details updated.')

                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_obj.pk, 'project_user_pk': project_user_obj.pk}))

            if project_user_update_form.is_valid():
                form_data = project_user_update_form.cleaned_data
                enable_notifications = form_data.get('enable_notifications')

                old_role = project_user_obj.role
                new_role = ProjectUserRoleChoice.objects.get(name=form_data.get('role'))
                demotion = False

                # demote manager to user role
                if old_role.name == 'Manager' and new_role.name == 'User':
                    if not managers.filter(~Q(pk=project_user_pk)).exists():

                        # no pis exist, cannot demote
                        if not project_pis.exists():
                            new_role = old_role
                            messages.error(
                                request, 'The project must have at least one PI or manager with notifications enabled.')

                        # enable all PI notifications, demote to user role
                        else:
                            for pi in project_pis:
                                pi.enable_notifications = True
                                pi.save()

                            # users have notifications disabled by default
                            enable_notifications = False
                            demotion = True

                            messages.warning(request, 'User {} is no longer a manager. All PIs will now receive notifications.'.format(
                                project_user_obj.user.username))
                            messages.success(request, 'User details updated.')

                    else:
                        demotion = True
                        messages.success(request, 'User details updated.')

                # promote user to manager role (notifications always active)
                elif old_role.name == 'User' and new_role.name == 'Manager':
                    enable_notifications = True
                    messages.success(request, 'User details updated.')

                project_user_obj.enable_notifications = enable_notifications
                project_user_obj.role = new_role
                project_user_obj.save()

                if demotion and not is_request_by_superuser:
                    return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_obj.pk, 'project_user_pk': project_user_obj.pk}))


def project_update_email_notification(request):

    if request.method == "POST":
        data = request.POST
        project_user_obj = get_object_or_404(
            ProjectUser, pk=data.get('user_project_id'))
        checked = data.get('checked')
        if checked == 'true':
            project_user_obj.enable_notifications = True
            project_user_obj.save()
            return HttpResponse('', status=200)
        elif checked == 'false':
            project_user_obj.enable_notifications = False
            project_user_obj.save()
            return HttpResponse('', status=200)
        else:
            return HttpResponse('', status=400)
    else:
        return HttpResponse('', status=400)


class ProjectReviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_review.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permissions to review this project.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if not project_obj.needs_review:
            messages.error(request, 'You do not need to review this project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if 'Auto-Import Project'.lower() in project_obj.title.lower():
            messages.error(
                request, 'You must update the project title before reviewing your project. You cannot have "Auto-Import Project" in the title.')
            return HttpResponseRedirect(reverse('project-update', kwargs={'pk': project_obj.pk}))

        if 'We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!' in project_obj.description:
            messages.error(
                request, 'You must update the project description before reviewing your project.')
            return HttpResponseRedirect(reverse('project-update', kwargs={'pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_review_form = ProjectReviewForm(project_obj.pk)

        context = {}
        context['project'] = project_obj
        context['project_review_form'] = project_review_form
        context['project_users'] = ', '.join(['{} {}'.format(ele.user.first_name, ele.user.last_name)
                                              for ele in project_obj.projectuser_set.filter(status__name='Active').order_by('user__last_name')])

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_review_form = ProjectReviewForm(project_obj.pk, request.POST)

        project_review_status_choice = ProjectReviewStatusChoice.objects.get(
            name='Pending')

        if project_review_form.is_valid():
            form_data = project_review_form.cleaned_data
            project_review_obj = ProjectReview.objects.create(
                project=project_obj,
                reason_for_not_updating_project=form_data.get('reason'),
                status=project_review_status_choice)

            project_obj.force_review = False
            project_obj.save()

            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse('project-review-list'))

            if EMAIL_ENABLED:
                send_email_template(
                    'New project review has been submitted',
                    'email/new_project_review.txt',
                    {'url': url},
                    EMAIL_SENDER,
                    [EMAIL_DIRECTOR_EMAIL_ADDRESS, ]
                )

            messages.success(request, 'Project reviewed successfully.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            messages.error(
                request, 'There was an error in processing  your project review.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))


class ProjectReviewListView(LoginRequiredMixin, UserPassesTestMixin, ListView):

    model = ProjectReview
    template_name = 'project/project_review_list.html'
    prefetch_related = ['project', ]
    context_object_name = 'project_review_list'

    def get_queryset(self):
        return ProjectReview.objects.filter(status__name='Pending')

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True

        messages.error(
            self.request, 'You do not have permission to review pending project reviews.')


class ProjectReviewCompleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True

        messages.error(
            self.request, 'You do not have permission to mark a pending project review as completed.')

    def get(self, request, project_review_pk):
        project_review_obj = get_object_or_404(
            ProjectReview, pk=project_review_pk)

        project_review_status_completed_obj = ProjectReviewStatusChoice.objects.get(
            name='Completed')
        project_review_obj.status = project_review_status_completed_obj
        project_review_obj.project.project_needs_review = False
        project_review_obj.save()

        messages.success(request, 'Project review for {} has been completed'.format(
            project_review_obj.project.title)
        )

        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReivewEmailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectReviewEmailForm
    template_name = 'project/project_review_email.html'
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True

        messages.error(
            self.request, 'You do not have permission to send email for a pending project review.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        context['project_review'] = project_review_obj

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.kwargs.get('pk'), **self.get_form_kwargs())

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        form_data = form.cleaned_data

        pi_users = project_review_obj.project.pis()
        receiver_list = [pi_user.email for pi_user in pi_users]
        cc = form_data.get('cc').strip()
        if cc:
            cc = cc.split(',')
        else:
            cc = []

        send_email(
            'Request for more information',
            form_data.get('email_body'),
            EMAIL_DIRECTOR_EMAIL_ADDRESS,
            receiver_list,
            cc=cc
        )

        if receiver_list:
            message = 'Email sent to:'
            for i, pi in enumerate(pi_users):
                message = message + (
                    f'\n{pi.first_name} {pi.last_name} ({pi.username})')
            messages.success(self.request, message)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-review-list')


class ProjectJoinView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        user_obj = self.request.user
        project_users = project_obj.projectuser_set.filter(user=user_obj)
        reason = self.request.POST.get('reason')

        if self.request.user.userprofile.access_agreement_signed_date is None:
            messages.error(
                self.request, 'You must sign the User Access Agreement before you can join a project.')
            return False

        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        if project_obj.status == inactive_project_status:
            message = (
                f'Project {project_obj.name} is inactive, and may not be '
                f'joined.')
            messages.error(self.request, message)
            return False

        if project_users.exists():
            project_user = project_users.first()
            if project_user.status.name == 'Active':
                message = (
                    f'You are already a member of Project {project_obj.name}.')
                messages.error(self.request, message)
                return False
            if project_user.status.name == 'Pending - Add':
                message = (
                    f'You have already requested to join Project '
                    f'{project_obj.name}.')
                messages.warning(self.request, message)
                return False

            pending_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Pending')
            processing_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')

            if ProjectUserRemovalRequest.objects. \
                    filter(project_user=project_user,
                           status__in=[pending_status, processing_status]).exists():
                message = (
                    f'You cannot join Project {project_obj.name} because you '
                    f'have a pending removal request for '
                    f'{project_obj.name}.')
                messages.error(self.request, message)
                return False

        # If the user is the requester or PI on a pending request for the
        # Project, do not allow the join request.
        if project_obj.name.startswith('vector_'):
            request_model = VectorProjectAllocationRequest
        else:
            request_model = SavioProjectAllocationRequest
        is_requester_or_pi = Q(requester=user_obj) | Q(pi=user_obj)
        if request_model.objects.filter(
                is_requester_or_pi, project=project_obj,
                status__name__in=['Under Review', 'Approved - Processing']):
            message = (
                f'You are the requester or PI of a pending request for '
                f'Project {project_obj.name}, so you may not join it. You '
                f'will automatically be added when it is approved.')
            messages.warning(self.request, message)
            return False

        if len(reason) < 20:
            message = 'Please provide a valid reason to join the project (min 20 characters)'
            messages.error(self.request, message)
            return False

        return True

    def get(self, *args, **kwargs):
        return redirect(self.login_url)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        user_obj = self.request.user
        project_users = project_obj.projectuser_set.filter(user=user_obj)
        role = ProjectUserRoleChoice.objects.get(name='User')
        status = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        reason = self.request.POST['reason']

        select_host_user_form = ProjectSelectHostUserForm(
            project=project_obj.name,
            data=self.request.POST)
        host_user = None
        if select_host_user_form.is_valid():
            host_user = \
                User.objects.get(
                    username=select_host_user_form.cleaned_data['host_user'])

        if project_users.exists():
            project_user = project_users.first()
            project_user.role = role
            # If the user is Active on the project, raise a warning and exit.
            if project_user.status.name == 'Active':
                message = (
                    f'You are already an Active member of Project '
                    f'{project_obj.name}.')
                messages.warning(self.request, message)
                next_view = reverse('project-join-list')
                return redirect(next_view)
            project_user.status = status
            project_user.save()
        else:
            project_user = ProjectUser.objects.create(
                user=user_obj,
                project=project_obj,
                role=role,
                status=status)

        # Create a join request
        ProjectUserJoinRequest.objects.create(project_user=project_user,
                                              reason=reason,
                                              host_user=host_user)

        message = (
            f'You have requested to join Project {project_obj.name}. The '
            f'managers have been notified.')
        messages.success(self.request, message)
        next_view = reverse('project-join-list')

        # Send a notification to the project managers.
        try:
            send_project_join_notification_email(project_obj, project_user)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.logger.error(message)
            self.logger.exception(e)

        return redirect(next_view)


class ProjectJoinListView(ProjectListView, UserPassesTestMixin):

    template_name = 'project/project_join_list.html'

    def test_func(self):
        user = self.request.user
        if user.userprofile.access_agreement_signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can join '
                'a project.')
            messages.error(self.request, message)
            return False
        return True

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        project_search_form = ProjectSearchForm(self.request.GET)

        projects = Project.objects.prefetch_related(
            'field_of_science', 'status').filter(
                status__name__in=['New', 'Active', ]
        ).annotate(
            cluster_name=Case(
                When(name='abc', then=Value('ABC')),
                When(name__startswith='vector_', then=Value('Vector')),
                default=Value('Savio'),
                output_field=CharField(),
            ),
        ).order_by(order_by)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data

            # Last Name
            if data.get('last_name'):
                pi_project_users = ProjectUser.objects.filter(
                    project__in=projects,
                    role__name='Principal Investigator',
                    user__last_name__icontains=data.get('last_name'))
                project_ids = pi_project_users.values_list(
                    'project_id', flat=True)
                projects = projects.filter(id__in=project_ids)

            # Username
            if data.get('username'):
                projects = projects.filter(
                    Q(projectuser__user__username__icontains=data.get(
                        'username')) &
                    (Q(projectuser__role__name='Principal Investigator') |
                     Q(projectuser__status__name='Active'))
                )

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get(
                        'field_of_science'))

            # Project Title
            if data.get('project_title'):
                projects = projects.filter(title__icontains=data.get('project_title'))

            # Project Name
            if data.get('project_name'):
                projects = projects.filter(name__icontains=data.get('project_name'))

            # Cluster Name
            if data.get('cluster_name'):
                projects = projects.filter(cluster_name__icontains=data.get('cluster_name'))

        return projects.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = self.get_queryset()
        user_obj = self.request.user

        # A User may not join a Project he/she is already a pending or active
        # member of.
        already_pending_or_active = set(projects.filter(
            projectuser__user=user_obj,
            projectuser__status__name__in=['Pending - Add', 'Active', ]
        ).values_list('name', flat=True))
        # A User may not join a Project with a pending
        # SavioProjectAllocationRequest where he/she is the requester or PI.
        is_requester_or_pi = Q(requester=user_obj) | Q(pi=user_obj)
        pending_project_request_statuses = [
            'Under Review', 'Approved - Processing']
        is_part_of_pending_savio_project_request = set(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'project'
            ).filter(
                is_requester_or_pi,
                status__name__in=pending_project_request_statuses
            ).values_list('project__name', flat=True))
        # A User may not join a Project with a pending
        # VectorProjectAllocationRequest where he/she is the requester or PI.
        is_part_of_pending_vector_project_request = set(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'project'
            ).filter(
                is_requester_or_pi,
                status__name__in=pending_project_request_statuses
            ).values_list('project__name', flat=True))
        pending_removal_requests = set([removal_request.project_user.project.name
                                        for removal_request in
                                        ProjectUserRemovalRequest.objects.filter(
                                            Q(project_user__user__username=self.request.user.username) &
                                            Q(status__name='Pending'))])

        not_joinable = set.union(
            already_pending_or_active,
            is_part_of_pending_savio_project_request,
            is_part_of_pending_vector_project_request,
            pending_removal_requests)

        join_requests = Project.objects.filter(Q(projectuser__user=self.request.user)
                                               & Q(status__name__in=['New', 'Active', ])
                                               & Q(projectuser__status__name__in=['Pending - Add']))\
            .annotate(cluster_name=Case(When(name='abc', then=Value('ABC')),
                                        When(name__startswith='vector_', then=Value('Vector')),
                                        default=Value('Savio'),
                                        output_field=CharField()))

        context['join_requests'] = join_requests
        context['not_joinable'] = not_joinable

        # Only non-LBL employees without a host user and without any pending
        # join requests need access to the SelectHostUserForm.
        context['need_host'] = False
        pending_status = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        if flag_enabled('LRC_ONLY') \
                and needs_host(self.request.user) \
                and not ProjectUser.objects.filter(user=self.request.user,
                                                   status=pending_status).exists():
            context['need_host'] = True

            selecthostform_dict = {}
            for project in context.get('project_list'):
                selecthostform_dict[project.name] = \
                    ProjectSelectHostUserForm(project=project.name)

            context['selecthostform_dict'] = selecthostform_dict

        return context


class ProjectReviewJoinRequestsView(LoginRequiredMixin, UserPassesTestMixin,
                                    TemplateView):
    template_name = 'project/project_review_join_requests.html'

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_view_all_projects'):
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            message = 'You cannot review join requests to an archived project.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def get_users_to_review(project_obj):
        users_to_review = []
        queryset = project_obj.projectuser_set.filter(
            status__name='Pending - Add').order_by('user__username')
        for ele in queryset:
            try:
                reason = ele.projectuserjoinrequest_set.latest('created').reason
            except ProjectUserJoinRequest.DoesNotExist:
                reason = ProjectUserJoinRequest.DEFAULT_REASON

            user = {
                'username': ele.user.username,
                'first_name': ele.user.first_name,
                'last_name': ele.user.last_name,
                'email': ele.user.email,
                'role': ele.role,
                'reason': reason
            }
            users_to_review.append(user)
        return users_to_review

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_review = self.get_users_to_review(project_obj)
        context = {}

        if users_to_review:
            formset = formset_factory(
                ProjectReviewUserJoinForm, max_num=len(users_to_review))
            formset = formset(initial=users_to_review, prefix='userform')
            context['formset'] = formset

        context['project'] = get_object_or_404(Project, pk=pk)

        context['can_add_users'] = False
        if self.request.user.is_superuser:
            context['can_add_users'] = True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            context['can_add_users'] = True

        if flag_enabled('LRC_ONLY'):
            host_dict = {}
            for user in users_to_review:
                username = user.get('username')
                host_dict[username] = \
                    ProjectUserJoinRequest.objects.filter(
                        project_user__project=project_obj,
                        project_user__user__username=username).latest('modified').host_user
            context['host_dict'] = host_dict

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        allowed_to_approve_users = False
        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            allowed_to_approve_users = True

        if self.request.user.is_superuser:
            allowed_to_approve_users = True

        if not allowed_to_approve_users:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('project-review-join-requests', kwargs={'pk': pk}))

        users_to_review = self.get_users_to_review(project_obj)

        formset = formset_factory(
            ProjectReviewUserJoinForm, max_num=len(users_to_review))
        formset = formset(
            request.POST, initial=users_to_review, prefix='userform')

        reviewed_users_count = 0

        decision = request.POST.get('decision', None)
        if decision not in ('approve', 'deny'):
            return HttpResponse('', status=400)

        if formset.is_valid():
            if decision == 'approve':
                status_name = 'Active'
                message_verb = 'Approved'
                email_function = send_project_join_request_approval_email
            else:
                status_name = 'Denied'
                message_verb = 'Denied'
                email_function = send_project_join_request_denial_email

            project_user_status_choice = \
                ProjectUserStatusChoice.objects.get(name=status_name)

            error_message = (
                'Unexpected server error. Please contact an administrator.')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))
                    project_user_obj = project_obj.projectuser_set.get(
                        user=user_obj)
                    project_user_obj.status = project_user_status_choice
                    project_user_obj.save()

                    if status_name == 'Active':
                        # Request cluster access.
                        request_runner = ProjectClusterAccessRequestRunner(
                            project_user_obj)
                        runner_result = request_runner.run()
                        if not runner_result.success:
                            messages.error(
                                self.request, runner_result.error_message)
                        # If the Project is a Vector project, automatically add
                        # the User to the designated Savio project for Vector
                        # users.
                        if project_obj.name.startswith('vector_'):
                            try:
                                add_vector_user_to_designated_savio_project(
                                    user_obj)
                            except Exception as e:
                                message = (
                                    f'Encountered unexpected exception when '
                                    f'automatically providing User '
                                    f'{user_obj.pk} with access to Savio. '
                                    f'Details:')
                                self.logger.error(message)
                                self.logger.exception(e)

                        # Set the host user if one is provided.
                        if flag_enabled('LRC_ONLY'):
                            host_user = \
                                ProjectUserJoinRequest.objects.filter(
                                    project_user__project=project_obj,
                                    project_user=project_user_obj).latest('modified').host_user

                            user_profile = user_obj.userprofile

                            if host_user:
                                if is_lbl_employee(user_obj) or not needs_host(user_obj):
                                    message = (
                                        f'User {user_obj.username} requested '
                                        f'a host user but already has '
                                        f'{user_profile.host_user.username} as '
                                        f'their host user.')
                                    self.logger.error(message)
                                else:
                                    user_profile.host_user = host_user
                                    user_profile.save()

                    # Send an email to the user.
                    try:
                        email_function(project_obj, project_user_obj)
                    except Exception as e:
                        message = (
                            'Failed to send notification email. Details:')
                        self.logger.error(message)
                        self.logger.exception(e)

            message = (
                f'{message_verb} {reviewed_users_count} user requests to join '
                f'the project. {settings.PROGRAM_NAME_SHORT} staff have been '
                f'notified to set up cluster access for each approved '
                f'request.')
            messages.success(request, message)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': pk}))


class ProjectJoinRequestListView(LoginRequiredMixin, UserPassesTestMixin,
                                 ListView):
    template_name = 'project/project_join_request_list.html'
    paginate_by = 25

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + 'created'
        else:
            order_by = '-created'

        project_join_requests = \
            ProjectUserJoinRequest.objects.filter(
                pk__in=ProjectUserJoinRequest.objects.filter(
                    project_user__status__name=
                    'Pending - Add').order_by(
                    'project_user', '-created').distinct(
                    'project_user'))

        join_request_search_form = JoinRequestSearchForm(self.request.GET)

        if join_request_search_form.is_valid():
            data = join_request_search_form.cleaned_data

            if data.get('username'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__user__username__icontains=data.get('username'))

            if data.get('email'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__user__email__icontains=data.get('email'))

            if data.get('project_name'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__project__name__icontains=data.get('project_name'))

        return project_join_requests.order_by(order_by)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_projectuserjoinrequest'):
            return True

        message = (
            'You do not have permission to view project join requests.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        join_request_search_form = JoinRequestSearchForm(self.request.GET)
        if join_request_search_form.is_valid():
            context['join_request_search_form'] = join_request_search_form
            data = join_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['join_request_search_form'] = join_request_search_form
        else:
            filter_parameters = None
            context['join_request_search_form'] = JoinRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        join_request_queryset = self.get_queryset()

        paginator = Paginator(join_request_queryset, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            join_requests = paginator.page(page)
        except PageNotAnInteger:
            join_requests = paginator.page(1)
        except EmptyPage:
            join_requests = paginator.page(paginator.num_pages)

        context['join_request_list'] = join_requests

        return context
