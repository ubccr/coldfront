import datetime
import pprint

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
                                             prorated_allocation_amount,
                                             request_project_cluster_access)
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
                                          ProjectUserUpdateForm)
from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectReviewStatusChoice,
                                           ProjectStatusChoice, ProjectUser,
                                           ProjectUserMessage,
                                           ProjectUserJoinRequest,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectAllocationRequestStatusChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.project.utils import (auto_approve_project_join_requests,
                                          get_project_compute_allocation,
                                          send_project_join_notification_email,
                                          send_project_request_denial_email,
                                          send_project_request_pooling_email)
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

        if project_obj.projectuser_set.filter(user=self.request.user, status__name='Active').exists():
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

        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True

        elif self.object.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.projectuser_set.get(user=self.request.user)

            if project_user.role.name in ['Principal Investigator', 'Manager']:
                context['username'] = project_user.user.username
                context['is_allowed_to_update_project'] = True

        # Retrieve cluster access statuses.
        cluster_access_statuses = {}
        try:
            allocation_obj = get_project_compute_allocation(self.object)
            statuses = \
                allocation_obj.allocationuserattribute_set.select_related(
                    'allocation_user__user'
                ).filter(
                    allocation_attribute_type__name='Cluster Account Status',
                    value__in=['Pending - Add', 'Active'])
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
                    status__name__in=['New', 'Active', ]
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
                    Q(status__name__in=['New', 'Active', ]) &
                    Q(projectuser__user=self.request.user) &
                    Q(projectuser__status__name='Active')
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
                Q(status__name__in=['New', 'Active', ]) &
                Q(projectuser__user=self.request.user) &
                Q(projectuser__status__name='Active')
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

        if self.request.user.userprofile.is_pi:
            return True

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

        message = (
            f'Join requests no longer require approval, so '
            f'{project_user_objs.count()} pending requests were automatically '
            f'approved.')

        if project_user_objs.exists():

            error_message = (
                'Unexpected server error. Please contact an administrator.')

            try:
                allocation_obj = get_project_compute_allocation(project_obj)
            except (Allocation.DoesNotExist,
                    Allocation.MultipleObjectsReturned):
                messages.error(self.request, error_message)
                return False

            for project_user_obj in project_user_objs:
                user_obj = project_user_obj.user
                try:
                    request_project_cluster_access(allocation_obj, user_obj)
                except ValueError:
                    message = (
                        f'User {user_obj.username} already has cluster access '
                        f'under Project {project_obj.name}.')
                    messages.warning(self.request, message)
                except Exception:
                    messages.error(self.request, error_message)
                    return False

            message = message + (
                ' BRC staff have been notified to set up cluster access for '
                'each request.')

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
            status__name='Active')]

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        matches = context.get('matches')
        for match in matches:
            match.update(
                {'role': ProjectUserRoleChoice.objects.get(name='User')})

        if matches:
            formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
            formset = formset(initial=matches, prefix='userform')

            # cache User objects
            match_users = User.objects.filter(username__in=[form._username for form in formset])
            for form in formset:

                # disable user matches with unsigned signed user agreement
                if not match_users.get(username=form._username)\
                        .userprofile.access_agreement_signed_date is not None:
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
                {'role': ProjectUserRoleChoice.objects.get(name='User')})

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
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    added_users_count += 1

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
                    error_message = (
                        'Unexpected server error. Please contact an '
                        'administrator.')
                    try:
                        allocation_obj = get_project_compute_allocation(
                            project_obj)
                    except (Allocation.DoesNotExist,
                            Allocation.MultipleObjectsReturned):
                        messages.error(self.request, error_message)
                        continue

                    try:
                        request_project_cluster_access(
                            allocation_obj, user_obj)
                    except ValueError:
                        message = (
                            f'User {user_obj.username} already has cluster '
                            f'access under Project {project_obj.name}.')
                        messages.warning(self.request, message)
                    except Exception:
                        messages.error(self.request, error_message)
                    else:
                        cluster_access_requests_count += 1

            if added_users_count != 0:
                messages.success(
                    request, 'Added {} users to project.'.format(added_users_count))

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
        users_to_remove = [

            {'username': ele.user.username,
             'first_name': ele.user.first_name,
             'last_name': ele.user.last_name,
             'email': ele.user.email,
             'role': ele.role}

            for ele in project_obj.projectuser_set.filter(
                status__name='Active').exclude(
                role__name='Principal Investigator').order_by(
                'user__username') if ele.user != self.request.user
        ]

        return users_to_remove

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(
                ProjectRemoveUserForm, max_num=len(users_to_remove))
            formset = formset(initial=users_to_remove, prefix='userform')
            context['formset'] = formset

        context['project'] = get_object_or_404(Project, pk=pk)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)

        formset = formset_factory(
            ProjectRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(
            request.POST, initial=users_to_remove, prefix='userform')

        remove_users_count = 0

        if formset.is_valid():
            project_user_removed_status_choice = ProjectUserStatusChoice.objects.get(
                name='Removed')
            allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(
                name='Removed')
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    remove_users_count += 1

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    if project_obj.projectuser_set.filter(
                            user=user_obj,
                            role__name='Principal Investigator').exists():
                        continue

                    project_user_obj = project_obj.projectuser_set.get(
                        user=user_obj)
                    project_user_obj.status = project_user_removed_status_choice
                    project_user_obj.save()

                    # get allocation to remove users from
                    allocations_to_remove_user_from = project_obj.allocation_set.filter(
                        status__name__in=['Active', 'New', 'Renewal Requested'])
                    for allocation in allocations_to_remove_user_from:
                        for allocation_user_obj in allocation.allocationuser_set.filter(user=user_obj, status__name__in=['Active', ]):
                            allocation_user_obj.status = allocation_user_removed_status_choice
                            allocation_user_obj.save()

                            allocation_remove_user.send(sender=self.__class__,
                                                        allocation_user_pk=allocation_user_obj.pk)

            messages.success(
                request, 'Removed {} users from project.'.format(remove_users_count))
        else:
            for error in formset.errors:
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
                initial={'role': project_user_obj.role, 'enable_notifications': project_user_obj.enable_notifications})

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

        if self.request.user.userprofile.access_agreement_signed_date is None:
            messages.error(
                self.request, 'You must sign the User Access Agreement before you can join a project.')
            return False

        if not project_users.exists():
            return True

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

        return True

    def get(self, *args, **kwargs):
        return redirect(self.login_url)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        user_obj = self.request.user
        project_users = project_obj.projectuser_set.filter(user=user_obj)
        role = ProjectUserRoleChoice.objects.get(name='User')
        status = ProjectUserStatusChoice.objects.get(name='Pending - Add')

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
        ProjectUserJoinRequest.objects.create(project_user=project_user)

        if project_obj.joins_auto_approval_delay != datetime.timedelta():
            message = (
                f'You have requested to join Project {project_obj.name}. The '
                f'managers have been notified. The request will automatically '
                f'be approved after a delay period, unless managers '
                f'explicitly deny it.')
            messages.success(self.request, message)
            next_view = reverse('project-join-list')
        else:
            next_view = reverse(
                'project-detail', kwargs={'pk': project_obj.pk})
            error_message = (
                'Unexpected server error. Please contact an administrator.')

            try:
                allocation_obj = get_project_compute_allocation(project_obj)
            except (Allocation.DoesNotExist,
                    Allocation.MultipleObjectsReturned):
                messages.error(self.request, error_message)
                return redirect(next_view)

            status = ProjectUserStatusChoice.objects.get(name='Active')
            project_user.status = status
            project_user.save()

            try:
                request_project_cluster_access(allocation_obj, user_obj)
            except ValueError:
                message = (
                    f'User {user_obj.username} already has cluster access '
                    f'under Project {project_obj.name}.')
                messages.warning(self.request, message)
            except Exception:
                messages.error(self.request, error_message)
            else:
                message = (
                    f'You have requested to join Project {project_obj.name}. '
                    f'Your request has automatically been approved. BRC staff '
                    f'have been notified to set up cluster access.')
                messages.success(self.request, message)
            next_view = reverse(
                'project-detail', kwargs={'pk': project_obj.pk})

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
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.access_agreement_signed_date is not None:
            return True

        messages.error(
            self.request, 'You must sign the User Access Agreement before you can join a project.')

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
        not_joinable = projects.filter(
            projectuser__user=self.request.user,
            projectuser__status__name__in=['Pending - Add', 'Active', ]
        ).values_list('name', flat=True)
        context['not_joinable'] = not_joinable
        return context


class ProjectReviewJoinRequestsView(LoginRequiredMixin, UserPassesTestMixin,
                                    TemplateView):
    template_name = 'project/project_review_join_requests.html'

    def test_func(self):
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
            user = {
                'username': ele.user.username,
                'first_name': ele.user.first_name,
                'last_name': ele.user.last_name,
                'email': ele.user.email,
                'role': ele.role,
                'auto_approval_time': auto_approval_time,
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
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

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
            else:
                status_name = 'Denied'
                message_verb = 'Denied'

            project_user_active_status_choice = \
                ProjectUserStatusChoice.objects.get(name=status_name)

            error_message = (
                'Unexpected server error. Please contact an administrator.')

            try:
                allocation_obj = get_project_compute_allocation(project_obj)
            except (Allocation.DoesNotExist,
                    Allocation.MultipleObjectsReturned):
                messages.error(self.request, error_message)
                return HttpResponseRedirect(
                    reverse('project-detail', kwargs={'pk': pk}))

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))
                    project_user_obj = project_obj.projectuser_set.get(
                        user=user_obj)
                    project_user_obj.status = project_user_active_status_choice
                    project_user_obj.save()
                    try:
                        request_project_cluster_access(
                            allocation_obj, user_obj)
                    except ValueError:
                        message = (
                            f'User {user_obj.username} already has cluster '
                            f'access under Project {project_obj.name}.')
                        messages.warning(self.request, message)
                    except Exception:
                        messages.error(self.request, error_message)
                        return HttpResponseRedirect(
                            reverse('project-detail', kwargs={'pk': pk}))

            message = (
                f'{message_verb} {reviewed_users_count} user requests to join '
                f'the project. BRC staff have been notified to set up cluster '
                f'access for each request.')
            messages.success(request, message)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': pk}))


class ProjectAutoApproveJoinRequestsView(LoginRequiredMixin,
                                         UserPassesTestMixin, View):

    def test_func(self):
        if self.request.user.is_superuser or self.request.user.is_staff:
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
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.project.forms import SavioProjectAllocationTypeForm
from coldfront.core.project.forms import SavioProjectDetailsForm
from coldfront.core.project.forms import SavioProjectExistingPIForm
from coldfront.core.project.forms import SavioProjectNewPIForm
from coldfront.core.project.forms import SavioProjectPoolAllocationsForm
from coldfront.core.project.forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.forms import SavioProjectReviewDenyForm
from coldfront.core.project.forms import SavioProjectReviewForm
from coldfront.core.project.forms import SavioProjectReviewSetupForm
from coldfront.core.project.forms import SavioProjectSurveyForm
from coldfront.core.project.forms import VectorProjectDetailsForm
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.user.models import UserProfile
from formtools.wizard.views import SessionWizardView


class ProjectRequestView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/project_request.html'

    def get(self, request, *args, **kwargs):
        context = dict()
        context['savio_requests'] = \
            SavioProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user))
        context['vector_requests'] = \
            VectorProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user))
        return render(request, self.template_name, context)


class SavioProjectRequestWizard(SessionWizardView):

    FORMS = [
        ('allocation_type', SavioProjectAllocationTypeForm),
        ('existing_pi', SavioProjectExistingPIForm),
        ('new_pi', SavioProjectNewPIForm),
        ('pool_allocations', SavioProjectPoolAllocationsForm),
        ('pooled_project_selection', SavioProjectPooledProjectSelectionForm),
        ('details', SavioProjectDetailsForm),
        ('survey', SavioProjectSurveyForm),
    ]

    TEMPLATES = {
        'allocation_type': 'project/project_request/savio/project_allocation_type.html',
        'existing_pi': 'project/project_request/savio/project_existing_pi.html',
        'new_pi': 'project/project_request/savio/project_new_pi.html',
        'pool_allocations': 'project/project_request/savio/project_pool_allocations.html',
        'pooled_project_selection': 'project/project_request/savio/project_pooled_project_selection.html',
        'details': 'project/project_request/savio/project_details.html',
        'survey': 'project/project_request/savio/project_survey.html',
    }

    form_list = [
        SavioProjectAllocationTypeForm,
        SavioProjectExistingPIForm,
        SavioProjectNewPIForm,
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
        'pool_allocations': 3,
        'pooled_project_selection': 4,
        'details': 5,
        'survey': 6,
    }

    logger = logging.getLogger(__name__)

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

        # Retrieve form data; include empty dictionaries for skipped steps.
        data = iter([form.cleaned_data for form in form_list])
        form_data = [{} for _ in range(len(self.form_list))]
        for step in sorted(form_dict.keys()):
            form_data[int(step)] = next(data)

        try:
            allocation_type = self.__get_allocation_type(form_data)
            pi = self.__handle_pi_data(form_data)
            pooling_requested = self.__get_pooling_requested(form_data)
            if pooling_requested:
                project = self.__handle_pool_with_existing_project(form_data)
            else:
                project = self.__handle_create_new_project(form_data)
            survey_data = self.__get_survey_data(form_data)

            # Store transformed form data in a request.
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Pending')
            SavioProjectAllocationRequest.objects.create(
                requester=self.request.user,
                allocation_type=allocation_type,
                pi=pi,
                project=project,
                pool=pooling_requested,
                survey_answers=survey_data,
                status=status)
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
        return data['pool']

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['survey']
        return form_data[step_number]

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
                description=data['description'],
                field_of_science=data['field_of_science'])
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
        pooled_project_selection_step = \
            self.step_numbers_by_form_name['pooled_project_selection']
        details_step = self.step_numbers_by_form_name['details']
        if step > details_step:
            pool_allocations_form_data = \
                self.get_cleaned_data_for_step(
                    str(pool_allocations_step))
            pooled_project_selection_form_data = \
                self.get_cleaned_data_for_step(
                    str(pooled_project_selection_step))
            details_form_data = self.get_cleaned_data_for_step(
                str(details_step))
            if pool_allocations_form_data['pool']:
                project = pooled_project_selection_form_data['project']
                dictionary.update({
                    'breadcrumb_project': f'Project: {project.name}'
                })
            else:
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


def show_pooled_project_selection_form_condition(wizard):
    step_name = 'pool_allocations'
    step = str(SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    return cleaned_data.get('pool', False)


class SavioProjectRequestListView(LoginRequiredMixin, UserPassesTestMixin,
                                  TemplateView):
    template_name = 'project/project_request/savio/project_request_list.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Filter out processed ones.
        savio_project_request_list = \
            SavioProjectAllocationRequest.objects.all()
        context['savio_project_request_list'] = savio_project_request_list
        return context


class SavioProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                    DetailView):
    model = SavioProjectAllocationRequest
    template_name = 'project/project_request/savio/project_request_detail.html'
    login_url = '/'
    context_object_name = 'savio_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    # TODO: Use the URL's name (reverse_lazy still leads to circular import).
    redirect = HttpResponseRedirect('savio-project-request-list/')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pk = self.kwargs.get('pk')
        request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)

        survey_form = SavioProjectSurveyForm(
            initial=request_obj.survey_answers, disable_fields=True)
        context['survey_form'] = survey_form

        try:
            context['allocation_amount'] = \
                self.__get_service_units_to_allocate(request_obj)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)

        if not self.request.user.is_superuser:
            message = 'You do not have permission to activate the request.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        # TODO: Check that the checklist steps are complete.
        if not self.__is_checklist_complete(request_obj):
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        try:
            self.__upgrade_pi_user(request_obj)
            project = self.__update_project(request_obj)
            self.__create_project_users(request_obj)
            allocation = self.__update_allocation(request_obj)

            request_obj.status = \
                ProjectAllocationRequestStatusChoice.objects.get(
                    name='Active')
            request_obj.save()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = (
                f'Project {project.name} and Allocation {allocation.pk} have '
                f'been activated.')
            messages.success(self.request, message)

        return self.redirect

    def __create_project_users(self, request_obj):
        """Create active ProjectUsers with the appropriate roles for the
        requester and/or the PI."""
        project = request_obj.project
        requester = request_obj.requester
        pi = request_obj.pi
        # get_or_create's 'defaults' arguments are only considered if a create
        # is required.
        defaults = {
            'status': ProjectUserStatusChoice.objects.get(name='Active')
        }
        if requester.pk != pi.pk:
            defaults['role'] = ProjectUserRoleChoice.objects.get(
                name='Manager')
            requester_project_user, _ = ProjectUser.objects.get_or_create(
                project=project, user=requester, defaults=defaults)
        defaults['role'] = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        pi_project_user, _ = ProjectUser.objects.get_or_create(
            project=project, user=pi, defaults=defaults)

    @staticmethod
    def __get_service_units_to_allocate(request_obj):
        """Return the number of service units to allocate to the
        project if it were to be approved now."""
        allocation_type = request_obj.allocation_type
        now = utc_now_offset_aware()
        if allocation_type == 'CO':
            return settings.CO_DEFAULT_ALLOCATION
        elif allocation_type == 'FCA':
            return prorated_allocation_amount(
                settings.FCA_DEFAULT_ALLOCATION, now)
        elif allocation_type == 'PCA':
            return prorated_allocation_amount(
                settings.PCA_DEFAULT_ALLOCATION, now)
        else:
            raise ValueError(f'Invalid allocation_type {allocation_type}.')

    def __is_checklist_complete(self, request_obj):
        # TODO
        return False

    def __update_allocation(self, request_obj):
        """Set the allocation's start and end dates. Set its attribute
        type. If not pooling, set its service units values; otherwise,
        increase it."""
        project = request_obj.project
        allocation_type = request_obj.allocation_type
        pool = request_obj.pool

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

        allocation = allocations.first()
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # TODO: Set start_date and end_date.
        # allocation.start_date = utc_now_offset_aware()
        # allocation.end_date =
        allocation.save()

        # Set the allocation's allocation type.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Savio Allocation Type')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation, defaults={'value': allocation_type})

        # Set or increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        # TODO: Pass the value here somehow. Put it in the form with default.
        from decimal import Decimal
        value = Decimal('0.00')
        if pool:
            existing_value = Decimal(allocation_attribute.value)
            allocation_attribute.value = str(existing_value + value)
        else:
            allocation_attribute.value = str(value)
        allocation_attribute.save()

        return allocation

    def __update_project(self, request_obj):
        """Set the Project to active, and store the survey answers."""
        project = request_obj.project
        project.status = ProjectStatusChoice.objects.get(name='Active')
        project.save()
        # TODO: Store the survey answers.
        return project

    @staticmethod
    def __upgrade_pi_user(request_obj):
        """Set the is_pi field of the request's PI UserProfile to
        True."""
        pi = request_obj.pi
        pi.userprofile.is_pi = True
        pi.userprofile.save()


class SavioProjectReviewEligibilityView(LoginRequiredMixin,
                                        UserPassesTestMixin, FormView):
    form_class = SavioProjectReviewForm
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

        if status == 'Denied':
            self.request_obj.status = \
                ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
            try:
                send_project_request_denial_email(self.request_obj)
            except Exception as e:
                message = 'Failed to send notification email. Details:'
                self.logger.error(message)
                self.logger.exception(e)

        self.request_obj.save()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        survey_form = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        context['survey_form'] = survey_form
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
                                      FormView):
    form_class = SavioProjectReviewForm
    template_name = (
        'project/project_request/savio/project_review_readiness.html')
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
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # TODO.
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['readiness'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }

        if status == 'Approved':
            if self.request_obj.pool:
                send_project_request_pooling_email(self.request_obj)
                # TODO: Leave a ProjectUserMessage for the poolee project.
                # ProjectUserMessage.objects.create(
                #     project=self.request_obj.project, author=, message='')
        elif status == 'Denied':
            self.request_obj.status = \
                ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
            try:
                send_project_request_denial_email(self.request_obj)
            except Exception as e:
                message = 'Failed to send notification email. Details:'
                self.logger.error(message)
                self.logger.exception(e)

        self.request_obj.save()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        survey_form = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        context['survey_form'] = survey_form
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


class SavioProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                  FormView):
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
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # TODO.
        form_data = form.cleaned_data
        status = form_data['status']
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': self.request_obj.project.name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        if status == 'Complete':
            # TODO
            pass
            # self.request_obj.status = \
            #     ProjectAllocationRequestStatusChoice.objects.get(name=)

        self.request_obj.save()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        survey_form = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        context['survey_form'] = survey_form
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['requested_name'] = self.request_obj.project.name
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
                                 FormView):
    form_class = SavioProjectReviewDenyForm
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
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }

        self.request_obj.status = \
            ProjectAllocationRequestStatusChoice.objects.get(name='Denied')
        try:
            send_project_request_denial_email(self.request_obj)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.logger.error(message)
            self.logger.exception(e)

        self.request_obj.save()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        survey_form = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        context['survey_form'] = survey_form
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


class VectorProjectRequestView(LoginRequiredMixin, FormView):
    form_class = VectorProjectDetailsForm
    template_name = 'project/project_request/vector/project_details.html'
    login_url = '/'

    logger = logging.getLogger(__name__)

    def form_valid(self, form):
        try:
            project = self.__handle_create_new_project(form.cleaned_data)
            # Store form data in a request.
            pi = User.objects.get(username=settings.VECTOR_PI_USERNAME)
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Pending')
            VectorProjectAllocationRequest.objects.create(
                requester=self.request.user,
                pi=pi,
                project=project,
                status=status)
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


class VectorProjectRequestListView(LoginRequiredMixin, UserPassesTestMixin,
                                   TemplateView):
    template_name = 'project/project_request/vector/project_request_list.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Filter out processed ones.
        vector_project_request_list = \
            VectorProjectAllocationRequest.objects.all()
        context['vector_project_request_list'] = vector_project_request_list
        return context


class VectorProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                     DetailView):
    model = VectorProjectAllocationRequest
    template_name = (
        'project/project_request/vector/project_request_detail.html')
    login_url = '/'
    context_object_name = 'vector_request'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        # TODO
        pass
