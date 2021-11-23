import datetime
import pprint
from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import Case, CharField, F, Q, Value, When
from django.forms import formset_factory
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserAttribute,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.utils import (get_allocation_user_cluster_access_status,
                                             prorated_allocation_amount)
from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user)
# from coldfront.core.grant.models import Grant
from coldfront.core.project.forms import (ProjectAddUserForm,
                                          ProjectAddUsersToAllocationForm,
                                          ProjectRemoveUserForm,
                                          ProjectReviewEmailForm,
                                          ProjectReviewForm,
                                          ProjectReviewUserJoinForm,
                                          ProjectSearchForm,
                                          ProjectUpdateForm,
                                          ProjectUserUpdateForm,
                                          ProjectRemovalRequestSearchForm,
                                          ProjectRemovalRequestUpdateStatusForm,
                                          ProjectRemovalRequestCompletionForm)
from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectReviewStatusChoice,
                                           ProjectStatusChoice, ProjectUser,
                                           ProjectUserMessage,
                                           ProjectUserJoinRequest,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectAllocationRequestStatusChoice,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice)
from coldfront.core.project.utils import (add_vector_user_to_designated_savio_project,
                                          auto_approve_project_join_requests,
                                          get_project_compute_allocation,
                                          ProjectClusterAccessRequestRunner,
                                          ProjectDenialRunner,
                                          SavioProjectApprovalRunner,
                                          send_added_to_project_notification_email,
                                          send_new_cluster_access_request_notification_email,
                                          send_project_join_notification_email,
                                          send_project_join_request_approval_email,
                                          send_project_join_request_denial_email,
                                          send_project_request_pooling_email,
                                          VectorProjectApprovalRunner,
                                          vector_request_denial_reason,)
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.project.utils_.renewal_utils import is_any_project_pi_renewable
from coldfront.core.project.utils_.request_utils import project_allocation_request_latest_update_timestamp
from coldfront.core.project.utils_.request_utils import savio_request_denial_reason
from coldfront.core.project.utils_.request_utils import vector_request_denial_reason
# from coldfront.core.publication.models import Publication
# from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.resource.models import Resource
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import (get_domain_url, import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email, send_email_template

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

        elif self.object.projectuser_set.filter(user=self.request.user).exists():
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

        if self.request.user.is_superuser or self.request.user.has_perm('allocation.can_view_all_allocations'):
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

        context['joins_auto_approved'] = (
            self.object.joins_auto_approval_delay == datetime.timedelta())

        context['join_request_delay_period'] = \
            str(self.object.joins_auto_approval_delay).rsplit(':', 1)[0]

        # Only display the "Renew Allowance" button for applicable allocation
        # types.
        # TODO: Display these for ic_ and pc_ when ready.
        context['renew_allowance_current_visible'] = \
            self.object.name.startswith('fc_')
            # self.object.name.startswith(('fc_', 'ic_', 'pc_'))
        # Only allow the "Renew Allowance" button to be clickable if any PIs do
        # not have pending/approved renewal requests.
        context['renew_allowance_current_clickable'] = (
            # Short-circuit if the button is not visible.
                context['renew_allowance_current_visible'] and
                is_any_project_pi_renewable(
                    self.object, get_current_allocation_period()))

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
        context['renew_allowance_current_visible'] = \
            ProjectUser.objects.filter(
                user=self.request.user, role__name__in=role_names,
                status=status)

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
        # If joins_auto_approval_delay is set to 0, automatically approve all
        # pending join requests.
        delay = form.cleaned_data['joins_auto_approval_delay']
        if delay == datetime.timedelta():
            if not self.__approve_pending_join_requests():
                return False
        return super().form_valid(form)

    def __approve_pending_join_requests(self):
        project_obj = self.get_object()
        active_status = ProjectUserStatusChoice.objects.get(name='Active')

        project_user_objs = project_obj.projectuser_set.filter(
            status__name='Pending - Add')
        for project_user_obj in project_user_objs:
            project_user_obj.status = active_status
            project_user_obj.save()

        for project_user_obj in project_user_objs:
            # Request cluster access.
            request_runner = ProjectClusterAccessRequestRunner(
                project_user_obj)
            runner_result = request_runner.run()
            if not runner_result.success:
                messages.error(self.request, runner_result.error_message)
            # Send an email to the user.
            try:
                send_project_join_request_approval_email(
                    project_obj, project_user_obj)
            except Exception as e:
                message = 'Failed to send notification email. Details:'
                self.logger.error(message)
                self.logger.exception(e)
            # If the Project is a Vector project, automatically add the
            # User to the designated Savio project for Vector users.
            if project_obj.name.startswith('vector_'):
                user_obj = project_user_obj.user
                try:
                    add_vector_user_to_designated_savio_project(user_obj)
                except Exception as e:
                    message = (
                        f'Encountered unexpected exception when '
                        f'automatically providing User {user_obj.pk} with '
                        f'access to Savio. Details:')
                    self.logger.error(message)
                    self.logger.exception(e)

        message = (
            f'Join requests no longer require approval, so '
            f'{project_user_objs.count()} pending requests were automatically '
            f'approved. BRC staff have been notified to set up cluster access '
            f'for each request.')
        messages.warning(self.request, message)

        return True


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
        if project_obj.status.name not in ['Active', 'New', ]:
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
        if project_obj.status.name not in ['Active', 'New', ]:
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
        if project_obj.status.name not in ['Active', 'New', ]:
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
                               status__in=[pending_status, processing_status]).exists():

                    message = f'Cannot add user {username} to project ' \
                              f'{project_obj.name} due to an active ' \
                              f'project removal request for the user. Please ' \
                              f'wait until it is completed before adding the ' \
                              f'user again.'
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


class ProjectRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_remove_users.html'
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
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot remove users from an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, project_obj):

        num_managers = project_obj.projectuser_set.filter(
            role__name='Manager',
            status__name='Active').count()

        if num_managers > 1:
            query_set = project_obj.projectuser_set.filter(
                status__name='Active').exclude(
                role__name='Principal Investigator').order_by(
                'user__username')
        else:
            query_set = project_obj.projectuser_set.filter(
                status__name='Active').exclude(
                role__name__in=['Principal Investigator', 'Manager']).order_by(
                'user__username')

        users_to_remove = [

            {'username': ele.user.username,
             'first_name': ele.user.first_name,
             'last_name': ele.user.last_name,
             'email': ele.user.email,
             'role': ele.role,
             'status': ele.status.name}

            for ele in query_set if ele.user != self.request.user
        ]

        users_pending_removal = [

            ele

            for ele in project_obj.projectuser_set.filter(
                status__name='Pending - Remove').exclude(
                role__name='Principal Investigator').order_by(
                'user__username')
        ]

        return users_to_remove, users_pending_removal

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove_list, users_pending_removal = self.get_users_to_remove(project_obj)
        context = {}
        context['project'] = get_object_or_404(Project, pk=pk)
        context['users_pending_removal'] = users_pending_removal

        page = request.GET.get('page', 1)

        paginator = Paginator(users_to_remove_list, 25)
        try:
            users_to_remove = paginator.page(page)
        except PageNotAnInteger:
            users_to_remove = paginator.page(1)
        except EmptyPage:
            users_to_remove = paginator.page(paginator.num_pages)

        context['users_to_remove'] = users_to_remove

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        user_obj = User.objects.get(
            username=self.request.POST['username'])

        try:
            request_runner = ProjectRemovalRequestRunner(
                self.request.user, user_obj, project_obj)
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for m in success_messages:
                    messages.success(request, m)
            else:
                for m in error_messages:
                    messages.error(request, m)

        except Exception as e:
            self.logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        # else:
        #     for error in formset.errors:
        #         messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectRemoveSelf(LoginRequiredMixin, UserPassesTestMixin, TemplateView):

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name='User',
                status__name='Active').exists():
            return True

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name='Manager',
                status__name='Active').exists() and \
                len(project_obj.projectuser_set.filter(role__name='Manager')) > 1:
            return True

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        try:
            request_runner = ProjectRemovalRequestRunner(
                self.request.user, self.request.user, project_obj)
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for message in success_messages:
                    messages.success(request, message)
            else:
                for message in error_messages:
                    messages.error(request, message)
        except Exception as e:
            self.logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return HttpResponseRedirect(reverse('home'))


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
            cc
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
                    filter(project_user=project_users.first(),
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

        # Create a join request, whose 'created' timestamp is used to determine
        # when to auto-approve the request.
        ProjectUserJoinRequest.objects.create(project_user=project_user,
                                              reason=reason)

        if project_obj.joins_auto_approval_delay != datetime.timedelta():
            message = (
                f'You have requested to join Project {project_obj.name}. The '
                f'managers have been notified. The request will automatically '
                f'be approved after a delay period, unless managers '
                f'explicitly deny it.')
            messages.success(self.request, message)
            next_view = reverse('project-join-list')
        else:
            # Activate the user.
            status = ProjectUserStatusChoice.objects.get(name='Active')
            project_user.status = status
            project_user.save()

            # Request cluster access.
            request_runner = ProjectClusterAccessRequestRunner(project_user)
            runner_result = request_runner.run()
            if runner_result.success:
                message = (
                    f'You have requested to join Project {project_obj.name}. '
                    f'Your request has automatically been approved. BRC staff '
                    f'have been notified to set up cluster access.')
                messages.success(self.request, message)
                next_view = reverse(
                    'project-detail', kwargs={'pk': project_obj.pk})
            else:
                messages.error(self.request, runner_result.error_message)

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
        not_joinable = set.union(
            already_pending_or_active,
            is_part_of_pending_savio_project_request,
            is_part_of_pending_vector_project_request)

        join_requests = Project.objects.filter(Q(projectuser__user=self.request.user)
                                               & Q(status__name__in=['New', 'Active', ])
                                               & Q(projectuser__status__name__in=['Pending - Add']))\
            .annotate(cluster_name=Case(When(name='abc', then=Value('ABC')),
                                        When(name__startswith='vector_', then=Value('Vector')),
                                        default=Value('Savio'),
                                        output_field=CharField()))

        for request in join_requests:
            delay = request.joins_auto_approval_delay
            project_user = request.projectuser_set.get(user=self.request.user)
            join_request_date = project_user.projectuserjoinrequest_set.latest('created').created
            auto_approval_time = join_request_date + delay
            request.auto_approval_time = auto_approval_time

        context['join_requests'] = join_requests
        context['not_joinable'] = not_joinable
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
        delay = project_obj.joins_auto_approval_delay

        users_to_review = []
        queryset = project_obj.projectuser_set.filter(
            status__name='Pending - Add').order_by('user__username')
        for ele in queryset:
            try:
                auto_approval_time = \
                    (ele.projectuserjoinrequest_set.latest('created').created +
                     delay)
            except ProjectUserJoinRequest.DoesNotExist:
                auto_approval_time = 'Unknown'

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
                'auto_approval_time': auto_approval_time,
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
                f'the project. BRC staff have been notified to set up cluster '
                f'access for each approved request.')
            messages.success(request, message)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': pk}))


class ProjectAutoApproveJoinRequestsView(LoginRequiredMixin,
                                         UserPassesTestMixin, View):

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        message = (
            'You do not have permission to automatically approve project '
            'requests.')
        messages.error(self.request, message)

    def post(self, request, *args, **kwargs):
        results = auto_approve_project_join_requests()
        num_processed = len(results)
        num_successes, num_failures = 0, 0
        for result in results:
            if result.success:
                num_successes = num_successes + 1
            else:
                num_failures = num_failures + 1
        message = (
            f'{num_processed} pending join requests were processed. '
            f'{num_successes} succeeded. {num_failures} failed.')
        if num_failures == 0:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return HttpResponseRedirect(
            reverse('allocation-cluster-account-request-list'))


# TODO: Once finalized, move these imports above.
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.forms import SavioProjectAllocationTypeForm
from coldfront.core.project.forms import SavioProjectDetailsForm
from coldfront.core.project.forms import SavioProjectExistingPIForm
from coldfront.core.project.forms import SavioProjectExtraFieldsForm
from coldfront.core.project.forms import SavioProjectICAExtraFieldsForm
from coldfront.core.project.forms import SavioProjectNewPIForm
from coldfront.core.project.forms import SavioProjectPoolAllocationsForm
from coldfront.core.project.forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms import SavioProjectReviewAllocationDatesForm
from coldfront.core.project.forms import SavioProjectReviewMemorandumSignedForm
from coldfront.core.project.forms import SavioProjectReviewSetupForm
from coldfront.core.project.forms import SavioProjectSurveyForm
from coldfront.core.project.forms import VectorProjectDetailsForm
from coldfront.core.project.forms import VectorProjectReviewSetupForm
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import savio_project_request_ica_extra_fields_schema
from coldfront.core.project.models import savio_project_request_ica_state_schema
from coldfront.core.project.models import savio_project_request_recharge_extra_fields_schema
from coldfront.core.project.models import savio_project_request_recharge_state_schema
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils import savio_request_state_status
from coldfront.core.project.utils import send_new_project_request_admin_notification_email
from coldfront.core.project.utils import send_new_project_request_pi_notification_email
from coldfront.core.project.utils import vector_request_state_status
from coldfront.core.user.models import UserProfile
from decimal import Decimal
from formtools.wizard.views import SessionWizardView
import iso8601
import pytz


class ProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                         TemplateView):
    template_name = 'project/project_request/project_request.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get(self, request, *args, **kwargs):
        context = dict()
        context['savio_requests'] = \
            SavioProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user)
            ).exclude(
                status__name__in=['Approved - Complete', 'Denied']
            )
        context['vector_requests'] = \
            VectorProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user)
            ).exclude(
                status__name__in=['Approved - Complete', 'Denied']
            )
        return render(request, self.template_name, context)


class SavioProjectRequestWizard(UserPassesTestMixin, SessionWizardView):

    FORMS = [
        ('allocation_type', SavioProjectAllocationTypeForm),
        ('existing_pi', SavioProjectExistingPIForm),
        ('new_pi', SavioProjectNewPIForm),
        ('ica_extra_fields', SavioProjectICAExtraFieldsForm),
        ('recharge_extra_fields', SavioProjectRechargeExtraFieldsForm),
        ('pool_allocations', SavioProjectPoolAllocationsForm),
        ('pooled_project_selection', SavioProjectPooledProjectSelectionForm),
        ('details', SavioProjectDetailsForm),
        ('survey', SavioProjectSurveyForm),
    ]

    TEMPLATES = {
        'allocation_type': 'project/project_request/savio/project_allocation_type.html',
        'existing_pi': 'project/project_request/savio/project_existing_pi.html',
        'new_pi': 'project/project_request/savio/project_new_pi.html',
        'ica_extra_fields': 'project/project_request/savio/project_ica_extra_fields.html',
        'recharge_extra_fields': 'project/project_request/savio/project_recharge_extra_fields.html',
        'pool_allocations': 'project/project_request/savio/project_pool_allocations.html',
        'pooled_project_selection': 'project/project_request/savio/project_pooled_project_selection.html',
        'details': 'project/project_request/savio/project_details.html',
        'survey': 'project/project_request/savio/project_survey.html',
    }

    form_list = [
        SavioProjectAllocationTypeForm,
        SavioProjectExistingPIForm,
        SavioProjectNewPIForm,
        SavioProjectICAExtraFieldsForm,
        SavioProjectRechargeExtraFieldsForm,
        SavioProjectPoolAllocationsForm,
        SavioProjectPooledProjectSelectionForm,
        SavioProjectDetailsForm,
        SavioProjectSurveyForm,
    ]

    # Non-required lookup table: form name --> step number
    step_numbers_by_form_name = {
        'allocation_type': 0,
        'existing_pi': 1,
        'new_pi': 2,
        'ica_extra_fields': 3,
        'recharge_extra_fields': 4,
        'pool_allocations': 5,
        'pooled_project_selection': 6,
        'details': 7,
        'survey': 8,
    }

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step):
        kwargs = {}
        step = int(step)
        # The names of steps that require the past data.
        step_names = [
            'existing_pi',
            'pooled_project_selection',
            'details',
            'survey',
        ]
        step_numbers = [
            self.step_numbers_by_form_name[name] for name in step_names]
        if step in step_numbers:
            self.__set_data_from_previous_steps(step, kwargs)
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, form_dict, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            # Retrieve form data; include empty dictionaries for skipped steps.
            data = iter([form.cleaned_data for form in form_list])
            form_data = [{} for _ in range(len(self.form_list))]
            for step in sorted(form_dict.keys()):
                form_data[int(step)] = next(data)

            request_kwargs = {
                'requester': self.request.user,
            }
            allocation_type = self.__get_allocation_type(form_data)
            pi = self.__handle_pi_data(form_data)
            if allocation_type == SavioProjectAllocationRequest.ICA:
                self.__handle_ica_allocation_type(form_data, request_kwargs)
            if allocation_type == SavioProjectAllocationRequest.RECHARGE:
                self.__handle_recharge_allocation_type(
                    form_data, request_kwargs)
            pooling_requested = self.__get_pooling_requested(form_data)
            if pooling_requested:
                project = self.__handle_pool_with_existing_project(form_data)
            else:
                project = self.__handle_create_new_project(form_data)
            survey_data = self.__get_survey_data(form_data)

            # Store transformed form data in a request.
            request_kwargs['allocation_type'] = allocation_type
            request_kwargs['pi'] = pi
            request_kwargs['project'] = project
            request_kwargs['pool'] = pooling_requested
            request_kwargs['survey_answers'] = survey_data
            request_kwargs['status'] = \
                ProjectAllocationRequestStatusChoice.objects.get(
                    name='Under Review')
            request = SavioProjectAllocationRequest.objects.create(
                **request_kwargs)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
            # Send a notification email to the PI if the requester differs.
            if request.requester != request.pi:
                try:
                    send_new_project_request_pi_notification_email(request)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return HttpResponseRedirect(redirect_url)

    def __get_allocation_type(self, form_data):
        """Return the allocation type matching the provided input."""
        step_number = self.step_numbers_by_form_name['allocation_type']
        data = form_data[step_number]
        allocation_type = data['allocation_type']
        for choice, _ in SavioProjectAllocationRequest.ALLOCATION_TYPE_CHOICES:
            if allocation_type == choice:
                return allocation_type
        self.logger.error(
            f'Form received unexpected allocation type {allocation_type}.')
        raise ValueError(f'Invalid allocation type {allocation_type}.')

    def __get_pooling_requested(self, form_data):
        """Return whether or not pooling was requested."""
        step_number = self.step_numbers_by_form_name['pool_allocations']
        data = form_data[step_number]
        return data.get('pool', False)

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['survey']
        return form_data[step_number]

    def __handle_ica_allocation_type(self, form_data, request_kwargs):
        """Perform ICA-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. Set the extra_fields field from the
        given form data and set the state field to include an additional
        step."""
        step_number = self.step_numbers_by_form_name['ica_extra_fields']
        data = form_data[step_number]
        extra_fields = savio_project_request_ica_extra_fields_schema()
        for field in extra_fields:
            extra_fields[field] = data[field]
        request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_ica_state_schema()

    def __handle_pi_data(self, form_data):
        """Return the requested PI. If the PI did not exist, create a
        new User and UserProfile."""
        # If an existing PI was selected, return the existing User object.
        step_number = self.step_numbers_by_form_name['existing_pi']
        data = form_data[step_number]
        if data['PI']:
            return data['PI']

        # Create a new User object intended to be a new PI.
        step_number = self.step_numbers_by_form_name['new_pi']
        data = form_data[step_number]
        try:
            email = data['email']
            pi = User.objects.create(
                username=email,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=email,
                is_active=False)
        except IntegrityError as e:
            self.logger.error(f'User {email} unexpectedly exists.')
            raise e

        # Set the user's middle name in the UserProfile; generate a PI request.
        try:
            pi_profile = pi.userprofile
        except UserProfile.DoesNotExist as e:
            self.logger.error(
                f'User {email} unexpectedly has no UserProfile.')
            raise e
        pi_profile.middle_name = data['middle_name']
        pi_profile.upgrade_request = utc_now_offset_aware()
        pi_profile.save()

        return pi

    def __handle_recharge_allocation_type(self, form_data, request_kwargs):
        """Perform Recharge-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. Set the extra_fields field from the
        given form data and set the state field to include an additional
        step."""
        step_number = self.step_numbers_by_form_name['recharge_extra_fields']
        data = form_data[step_number]
        extra_fields = savio_project_request_recharge_extra_fields_schema()
        for field in extra_fields:
            extra_fields[field] = data[field]
        request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_recharge_state_schema()

    def __handle_create_new_project(self, form_data):
        """Create a new project and an allocation to the Savio Compute
        resource."""
        step_number = self.step_numbers_by_form_name['details']
        data = form_data[step_number]

        # Create the new Project.
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
                #field_of_science=data['field_of_science'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Savio Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project

    def __handle_pool_with_existing_project(self, form_data):
        """Return the requested project to pool with."""
        step_number = \
            self.step_numbers_by_form_name['pooled_project_selection']
        data = form_data[step_number]
        project = data['project']

        # Validate that the project has exactly one allocation to the "Savio
        # Compute" resource.
        resource = Resource.objects.get(name='Savio Compute')
        allocations = Allocation.objects.filter(
            project=project, resources__pk__exact=resource.pk)
        try:
            assert allocations.count() == 1
        except AssertionError as e:
            number = 'no' if allocations.count() == 0 else 'more than one'
            self.logger.error(
                f'Project {project.name} unexpectedly has {number} Allocation '
                f'to Resource {resource.name}')
            raise e

        return project

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        allocation_type_form_step = \
            self.step_numbers_by_form_name['allocation_type']
        if step > allocation_type_form_step:
            allocation_type_form_data = self.get_cleaned_data_for_step(
                str(allocation_type_form_step))
            if allocation_type_form_data:
                dictionary.update(allocation_type_form_data)

        existing_pi_step = self.step_numbers_by_form_name['existing_pi']
        new_pi_step = self.step_numbers_by_form_name['new_pi']
        if step > new_pi_step:
            existing_pi_form_data = self.get_cleaned_data_for_step(
                str(existing_pi_step))
            new_pi_form_data = self.get_cleaned_data_for_step(str(new_pi_step))
            if existing_pi_form_data['PI'] is not None:
                pi = existing_pi_form_data['PI']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'Existing PI: {pi.first_name} {pi.last_name} '
                        f'({pi.email})')
                })
            else:
                first_name = new_pi_form_data['first_name']
                last_name = new_pi_form_data['last_name']
                email = new_pi_form_data['email']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'New PI: {first_name} {last_name} ({email})')
                })

        pool_allocations_step = \
            self.step_numbers_by_form_name['pool_allocations']
        if step > pool_allocations_step:
            allocation_type = dictionary['allocation_type']
            non_poolable_allocation_types = (
                SavioProjectAllocationRequest.ICA,
                SavioProjectAllocationRequest.RECHARGE,
            )
            if allocation_type not in non_poolable_allocation_types:
                pool_allocations_form_data = self.get_cleaned_data_for_step(
                    str(pool_allocations_step))
                pooling_requested = pool_allocations_form_data['pool']
            else:
                pooling_requested = False
            dictionary.update({'breadcrumb_pooling': pooling_requested})

        pooled_project_selection_step = \
            self.step_numbers_by_form_name['pooled_project_selection']
        details_step = self.step_numbers_by_form_name['details']
        if step > details_step:
            if pooling_requested:
                pooled_project_selection_form_data = \
                    self.get_cleaned_data_for_step(
                        str(pooled_project_selection_step))
                project = pooled_project_selection_form_data['project']
                dictionary.update({
                    'breadcrumb_project': f'Project: {project.name}'
                })
            else:
                details_form_data = self.get_cleaned_data_for_step(
                    str(details_step))
                name = details_form_data['name']
                dictionary.update({'breadcrumb_project': f'Project: {name}'})


def show_details_form_condition(wizard):
    step_name = 'pool_allocations'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    return not cleaned_data.get('pool', False)


def show_new_pi_form_condition(wizard):
    step_name = 'existing_pi'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    return cleaned_data.get('PI', None) is None


def show_ica_extra_fields_form_condition(wizard):
    step_name = 'allocation_type'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    ica_allocation_type = SavioProjectAllocationRequest.ICA
    return cleaned_data.get('allocation_type', None) == ica_allocation_type


def show_recharge_extra_fields_form_condition(wizard):
    step_name = 'allocation_type'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    recharge_allocation_type = SavioProjectAllocationRequest.RECHARGE
    return (
        cleaned_data.get('allocation_type', None) == recharge_allocation_type)


def show_pool_allocations_form_condition(wizard):
    step_name = 'allocation_type'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    non_poolable_allocation_types = (
        SavioProjectAllocationRequest.ICA,
        SavioProjectAllocationRequest.RECHARGE,
    )
    allocation_type = cleaned_data.get('allocation_type', None)
    return allocation_type not in non_poolable_allocation_types


def show_pooled_project_selection_form_condition(wizard):
    step_name = 'pool_allocations'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    return cleaned_data.get('pool', False)


class SavioProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/savio/project_request_list.html'
    login_url = '/'
    # Show completed requests if True; else, show pending requests.
    completed = False

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

        return SavioProjectAllocationRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)
        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        if not (user.is_superuser or user.has_perm('project.view_savioprojectallocationrequest')):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['savio_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SavioProjectRequestMixin(object):

    @staticmethod
    def get_extra_fields_form(allocation_type, extra_fields):
        kwargs = {
            'initial': extra_fields,
            'disable_fields': True,
        }
        if allocation_type == SavioProjectAllocationRequest.ICA:
            form = SavioProjectICAExtraFieldsForm
        elif allocation_type == SavioProjectAllocationRequest.RECHARGE:
            form = SavioProjectRechargeExtraFieldsForm
        else:
            form = SavioProjectExtraFieldsForm
        return form(**kwargs)


class SavioProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                    SavioProjectRequestMixin, DetailView):
    model = SavioProjectAllocationRequest
    template_name = 'project/project_request/savio/project_request_detail.html'
    login_url = '/'
    context_object_name = 'savio_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('savio-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_savioprojectallocationrequest'):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)

        try:
            context['allocation_amount'] = \
                self.__get_service_units_to_allocate()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'

        try:
            latest_update_timestamp = \
                project_allocation_request_latest_update_timestamp(
                    self.request_obj)
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = savio_request_denial_reason(self.request_obj)
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['setup_status'] = self.__get_setup_status()
        context['is_checklist_complete'] = self.__is_checklist_complete()

        context['is_allowed_to_manage_request'] = self.request.user.is_superuser

        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        try:
            num_service_units = self.__get_service_units_to_allocate()
            runner = SavioProjectApprovalRunner(
                self.request_obj, num_service_units)
            project, allocation = runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = (
                f'Project {project.name} and Allocation {allocation.pk} have '
                f'been activated. A cluster access request has automatically '
                f'been made for the requester.')
            messages.success(self.request, message)

        # Send any messages from the runner back to the user.
        try:
            for message in runner.get_user_messages():
                messages.info(self.request, message)
        except NameError:
            pass

        return HttpResponseRedirect(self.redirect)

    def __get_service_units_to_allocate(self):
        """Return the number of service units to allocate to the project
        if it were to be approved now.

        If the request was created as part of an allocation renewal, it
        may be associated with at most one AllocationRenewalRequest. If
        so, service units will be allocated when the latter request is
        approved."""
        if AllocationRenewalRequest.objects.filter(
                new_project_request=self.request_obj).exists():
            return settings.ALLOCATION_MIN

        allocation_type = self.request_obj.allocation_type
        now = utc_now_offset_aware()
        if allocation_type == SavioProjectAllocationRequest.CO:
            return settings.CO_DEFAULT_ALLOCATION
        elif allocation_type == SavioProjectAllocationRequest.FCA:
            return prorated_allocation_amount(
                settings.FCA_DEFAULT_ALLOCATION, now)
        elif allocation_type == SavioProjectAllocationRequest.ICA:
            return settings.ICA_DEFAULT_ALLOCATION
        elif allocation_type == SavioProjectAllocationRequest.PCA:
            return prorated_allocation_amount(
                settings.PCA_DEFAULT_ALLOCATION, now)
        elif allocation_type == SavioProjectAllocationRequest.RECHARGE:
            num_service_units = \
                self.request_obj.extra_fields['num_service_units']
            return Decimal(f'{num_service_units:.2f}')
        else:
            raise ValueError(f'Invalid allocation_type {allocation_type}.')

    def __get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        allocation_type = self.request_obj.allocation_type
        state = self.request_obj.state
        if (state['eligibility']['status'] == 'Denied' or
                state['readiness']['status'] == 'Denied'):
            return 'N/A'
        else:
            pending = 'Pending'
            ica = SavioProjectAllocationRequest.ICA
            recharge = SavioProjectAllocationRequest.RECHARGE
            if allocation_type in (ica, recharge):
                if allocation_type == ica:
                    if state['allocation_dates']['status'] == pending:
                        return pending
                if state['memorandum_signed']['status'] == pending:
                    return pending
        return state['setup']['status']

    def __is_checklist_complete(self):
        status_choice = savio_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class SavioProjectReviewEligibilityView(LoginRequiredMixin,
                                        UserPassesTestMixin,
                                        SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_eligibility.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewReadinessView(LoginRequiredMixin, UserPassesTestMixin,
                                      SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_readiness.html')
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['readiness'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Approved':
            if self.request_obj.pool:
                try:
                    send_project_request_pooling_email(self.request_obj)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        elif status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Readiness status for request {self.request_obj.pk} has been set '
            f'to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['savio_request'] = self.request_obj
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        readiness = self.request_obj.state['readiness']
        initial['status'] = readiness['status']
        initial['justification'] = readiness['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewAllocationDatesView(LoginRequiredMixin,
                                            UserPassesTestMixin,
                                            SavioProjectRequestMixin,
                                            FormView):
    form_class = SavioProjectReviewAllocationDatesForm
    template_name = (
        'project/project_request/savio/project_review_allocation_dates.html')
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        allocation_type = self.request_obj.allocation_type
        if allocation_type != SavioProjectAllocationRequest.ICA:
            message = (
                f'This view is not applicable for projects with allocation '
                f'type {allocation_type}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        # The allocation starts at the beginning of the start date and ends at
        # the end of the end date.
        local_tz = pytz.timezone('America/Los_Angeles')
        tz = pytz.timezone(settings.TIME_ZONE)
        if form_data['start_date']:
            naive_dt = datetime.datetime.combine(
                form_data['start_date'], datetime.datetime.min.time())
            start = local_tz.localize(naive_dt).astimezone(tz).isoformat()
        else:
            start = ''
        if form_data['end_date']:
            naive_dt = datetime.datetime.combine(
                form_data['end_date'], datetime.datetime.max.time())
            end = local_tz.localize(naive_dt).astimezone(tz).isoformat()
        else:
            end = ''

        self.request_obj.state['allocation_dates'] = {
            'status': status,
            'dates': {
                'start': start,
                'end': end,
            },
            'timestamp': timestamp,
        }

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Allocation Dates status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        allocation_dates = self.request_obj.state['allocation_dates']
        initial['status'] = allocation_dates['status']
        local_tz = pytz.timezone('America/Los_Angeles')
        for key in ('start', 'end'):
            value = allocation_dates['dates'][key]
            if value:
                initial[f'{key}_date'] = iso8601.parse_date(value).astimezone(
                    pytz.utc).astimezone(local_tz).date()
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewMemorandumSignedView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             SavioProjectRequestMixin,
                                             FormView):
    form_class = SavioProjectReviewMemorandumSignedForm
    template_name = (
        'project/project_request/savio/project_review_memorandum_signed.html')
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        allocation_type = self.request_obj.allocation_type
        memorandum_types = (
            SavioProjectAllocationRequest.ICA,
            SavioProjectAllocationRequest.RECHARGE,
        )
        if allocation_type not in memorandum_types:
            message = (
                f'This view is not applicable for projects with allocation '
                f'type {allocation_type}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        self.request_obj.state['memorandum_signed'] = {
            'status': status,
            'timestamp': timestamp,
        }

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Memorandum Signed status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        memorandum_signed = self.request_obj.state['memorandum_signed']
        initial['status'] = memorandum_signed['status']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                  SavioProjectRequestMixin, FormView):
    form_class = SavioProjectReviewSetupForm
    template_name = 'project/project_request/savio/project_review_setup.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = savio_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewDenyView(LoginRequiredMixin, UserPassesTestMixin,
                                 SavioProjectRequestMixin, FormView):
    form_class = ReviewDenyForm
    template_name = (
        'project/project_request/savio/project_review_deny.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        runner = ProjectDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.pk} has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                               FormView):
    form_class = VectorProjectDetailsForm
    template_name = 'project/project_request/vector/project_details.html'
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perms('project.view_vectorprojectallocationrequest'):
            return True

        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def form_valid(self, form):
        try:
            project = self.__handle_create_new_project(form.cleaned_data)
            # Store form data in a request.

            pi = User.objects.get(username=settings.VECTOR_PI_USERNAME)
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
            request = VectorProjectAllocationRequest.objects.create(
                requester=self.request.user,
                pi=pi,
                project=project,
                status=status)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')

    def __handle_create_new_project(self, data):
        """Create a new project and an allocation to the Vector Compute
        resource."""
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Vector Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Vector Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project


class VectorProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/vector/project_request_list.html'
    login_url = '/'
    # Show completed requests if True; else, show pending requests.
    completed = False

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
        return VectorProjectAllocationRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        user = self.request.user

        request_list = self.get_queryset()
        permission = 'project.view_vectorprojectallocationrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['vector_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class VectorProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                     DetailView):
    model = VectorProjectAllocationRequest
    template_name = (
        'project/project_request/vector/project_request_detail.html')
    login_url = '/'
    context_object_name = 'vector_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('vector-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        permission = 'project.view_vectorprojectallocationrequest'
        if self.request.user.has_perm(permission):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            latest_update_timestamp = \
                project_allocation_request_latest_update_timestamp(
                    self.request_obj)
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = vector_request_denial_reason(self.request_obj)
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['is_checklist_complete'] = self.__is_checklist_complete()

        context['is_allowed_to_manage_request'] = (
            self.request.user.is_superuser)

        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))

        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
        try:
            runner = VectorProjectApprovalRunner(self.request_obj)
            project, allocation = runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = (
                f'Project {project.name} and Allocation {allocation.pk} have '
                f'been activated. A cluster access request has automatically '
                f'been made for the requester.')
            messages.success(self.request, message)

        # Send any messages from the runner back to the user.
        try:
            for message in runner.get_user_messages():
                messages.info(self.request, message)
        except NameError:
            pass

        return HttpResponseRedirect(self.redirect)

    def __is_checklist_complete(self):
        status_choice = vector_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class VectorProjectReviewEligibilityView(LoginRequiredMixin,
                                         UserPassesTestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/vector/project_review_eligibility.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = vector_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                   FormView):
    form_class = VectorProjectReviewSetupForm
    template_name = 'project/project_request/vector/project_review_setup.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = vector_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            SavioProjectAllocationRequest, pk=self.kwargs.get('pk'))

        state_status = savio_request_state_status(project_request)
        denied_status = ProjectAllocationRequestStatusChoice.objects.get(name='Denied')

        if state_status != denied_status:
            message = 'Savio project request has an unexpected status.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('savio-project-request-detail',
                        kwargs={'pk': self.kwargs.get('pk')}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            SavioProjectAllocationRequest, pk=kwargs.get('pk'))
        
        if project_request.state['eligibility']['status'] == 'Denied':
            project_request.state['eligibility']['status'] = 'Pending'

        if project_request.state['readiness']['status'] == 'Denied':
            project_request.state['readiness']['status'] = 'Pending'
            
        if project_request.state['other']['timestamp']:
            project_request.state['other']['justification'] = ''
            project_request.state['other']['timestamp'] = ''

        project_request.status = savio_request_state_status(project_request)
        project_request.save()

        message = (
            f'Project request {project_request.project.name} '
            f'has been UNDENIED and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse('savio-project-request-detail',
                    kwargs={'pk': kwargs.get('pk')}))


class VectorProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            VectorProjectAllocationRequest, pk=self.kwargs.get('pk'))

        state_status = vector_request_state_status(project_request)
        denied_status = ProjectAllocationRequestStatusChoice.objects.get(name='Denied')

        if state_status != denied_status:
            message = 'Vector project request has an unexpected status.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('vector-project-request-detail',
                        kwargs={'pk': self.kwargs.get('pk')}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            VectorProjectAllocationRequest, pk=kwargs.get('pk'))

        if project_request.state['eligibility']['status'] == 'Denied':
            project_request.state['eligibility']['status'] = 'Pending'

        project_request.status = vector_request_state_status(project_request)
        project_request.save()

        message = (
            f'Project request {project_request.project.name} '
            f'has been UNDENIED and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse('vector-project-request-detail',
                    kwargs={'pk': kwargs.get('pk')}))


class ProjectRemovalRequestListView(LoginRequiredMixin,
                                    UserPassesTestMixin,
                                    ListView):
    template_name = 'project/project_removal_request_list.html'
    login_url = '/'
    completed = False
    paginate_by = 30
    context_object_name = "project_removal_request_list"

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

        project_removal_status_complete, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
            name='Complete')

        project_removal_status_pending, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name='Pending')

        project_removal_status_processing, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name='Processing')

        project_removal_status_not_complete = [project_removal_status_pending,
                                               project_removal_status_processing]

        removal_request_search_form = ProjectRemovalRequestSearchForm(self.request.GET)

        if self.completed:
            project_removal_request_list = ProjectUserRemovalRequest.objects.filter(
                status=project_removal_status_complete)
        else:
            project_removal_request_list = ProjectUserRemovalRequest.objects.filter(
                status__in=project_removal_status_not_complete)

        if removal_request_search_form.is_valid():
            data = removal_request_search_form.cleaned_data

            if data.get('username'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__user__username__icontains=data.get(
                            'username'))

            if data.get('email'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__user__email__icontains=data.get(
                            'email'))

            if data.get('project_name'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__project__name__icontains=data.get(
                            'project_name'))

            if data.get('requester'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        requester__user__username__icontains=data.get(
                            'username'))

        return project_removal_request_list.order_by(order_by)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_projectuserremovalrequest'):
            return True

        message = (
            'You do not have permission to review project removal requests.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        removal_request_search_form = ProjectRemovalRequestSearchForm(self.request.GET)
        if removal_request_search_form.is_valid():
            context['removal_request_search_form'] = removal_request_search_form
            data = removal_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['removal_request_search_form'] = removal_request_search_form
        else:
            filter_parameters = None
            context['removal_request_search_form'] = ProjectRemovalRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = "toggle"

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')
        removal_request_list = self.get_queryset()

        paginator = Paginator(removal_request_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            removal_requests = paginator.page(page)
        except PageNotAnInteger:
            removal_requests = paginator.page(1)
        except EmptyPage:
            removal_requests = paginator.page(paginator.num_pages)

        context['removal_request_list'] = removal_requests

        return context


class ProjectRemovalRequestUpdateStatusView(LoginRequiredMixin,
                                            UserPassesTestMixin, FormView):
    form_class = ProjectRemovalRequestUpdateStatusForm
    login_url = '/'
    template_name = (
        'project/project_removal_request_update_status.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to update project removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.project_removal_request_obj = get_object_or_404(
            ProjectUserRemovalRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.project_removal_request_obj.project_user.user
        status = self.project_removal_request_obj.status.name
        if status != 'Pending':
            message = f'Project removal request has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-removal-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        project_removal_status_choice, _ =\
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name=status)
        self.project_removal_request_obj.status = project_removal_status_choice
        self.project_removal_request_obj.save()

        message = (
            f'Project removal request initiated by '
            f'{self.project_removal_request_obj.requester.username} for User '
            f'{self.user_obj.username} under '
            f'Project {self.project_removal_request_obj.project_user.project.name} '
            f'has been marked as {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_removal_request'] = self.project_removal_request_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.project_removal_request_obj.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('project-removal-request-list')


class ProjectRemovalRequestCompleteStatusView(LoginRequiredMixin,
                                              UserPassesTestMixin,
                                              FormView):
    form_class = ProjectRemovalRequestCompletionForm
    login_url = '/'
    template_name = (
        'project/project_removal_request_complete_status.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to update project removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.project_removal_request_obj = get_object_or_404(
            ProjectUserRemovalRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.project_removal_request_obj.project_user.user
        status = self.project_removal_request_obj.status.name
        if status != 'Processing':
            message = f'Project removal request has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-removal-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        project_removal_status_choice, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name=status)

        project_obj = self.project_removal_request_obj.project_user.project
        removed_user = self.project_removal_request_obj.project_user
        requester = self.project_removal_request_obj.requester

        self.project_removal_request_obj.status = project_removal_status_choice
        if status == 'Complete':
            self.project_removal_request_obj.completion_time = utc_now_offset_aware()
        self.project_removal_request_obj.save()

        if status == 'Complete':
            project_user_status_removed, _ = \
                ProjectUserStatusChoice.objects.get_or_create(
                    name='Removed')
            removed_user.status = project_user_status_removed
            removed_user.save()

        message = (
            f'Project removal request initiated by '
            f'{self.project_removal_request_obj.requester.username} for User '
            f'{self.user_obj.username} under '
            f'Project {self.project_removal_request_obj.project_user.project.name} '
            f'has been marked as {status}.')
        messages.success(self.request, message)

        if EMAIL_ENABLED and status == 'Complete':
            manager_pi_queryset = project_obj.projectuser_set.filter(
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active')

            for proj_user in list(chain(manager_pi_queryset, [removed_user])):
                curr_user = proj_user.user
                template_context = {
                    'user_first_name': curr_user.first_name,
                    'user_last_name': curr_user.last_name,
                    'removed_user_first_name': removed_user.user.first_name,
                    'removed_user_last_name': removed_user.user.last_name,
                    'requester_first_name': requester.first_name,
                    'requester_last_name': requester.last_name,
                    'project_name': project_obj.name,
                    'signature': EMAIL_SIGNATURE,
                    'support_email': SUPPORT_EMAIL,
                }

                send_email_template(
                    'Project Removal Request Completed',
                    'email/project_removal/project_removal_complete.txt',
                    template_context,
                    EMAIL_SENDER,
                    [curr_user.email]
                )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_removal_request'] = self.project_removal_request_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.project_removal_request_obj.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('project-removal-request-list')

