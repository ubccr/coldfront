import datetime
import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.utils import generate_guauge_data_from_usage
from coldfront.core.allocation.models import (
    Allocation,
    AllocationUser,
    AllocationStatusChoice,
    AllocationUserStatusChoice,
)
from coldfront.core.allocation.signals import (
    allocation_remove_user,
    allocation_activate_user,
)
from coldfront.core.project.signals import (
    project_filter_users_to_remove,
    project_preremove_projectuser,
    project_make_projectuser,
    project_create,
    project_post_create
)
from coldfront.core.grant.models import Grant
from coldfront.core.project.forms import (
    ProjectReviewForm,
    ProjectSearchForm,
    ProjectAddUserForm,
    ProjectRemoveUserForm,
    ProjectUserUpdateForm,
    ProjectReviewEmailForm,
    ProjectAttributeAddForm,
    ProjectAttributeDeleteForm,
    ProjectAttributeUpdateForm,
    ProjectAddUsersToAllocationForm,
)
from coldfront.core.project.models import (
    Project,
    ProjectUser,
    ProjectReview,
    ProjectAttribute,
    ProjectPermission,
    ProjectUserMessage,
    ProjectStatusChoice,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
    ProjectReviewStatusChoice,
)
from coldfront.core.project.utils import generate_usage_history_graph
from coldfront.core.publication.models import Publication
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.views import ColdfrontListView, NoteCreateView, NoteUpdateView
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.fasrc import sort_by
from coldfront.core.utils.mail import send_email, send_email_template

if 'django_q' in settings.INSTALLED_APPS:
    from django_q.tasks import Task

ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)


EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings('EMAIL_DIRECTOR_EMAIL_ADDRESS')
EMAIL_SENDER = import_from_settings('EMAIL_SENDER')


def produce_filter_parameter(key, value):
    if isinstance(value, list):
        return ''.join([f'{key}={ele}&' for ele in value])
    return f'{key}={value}&'

logger = logging.getLogger(__name__)


class ProjectDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Project
    template_name = 'project/project_detail.html'
    context_object_name = 'project'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.has_perm('project.can_view_all_projects'):
            return True

        project_obj = self.get_object()
        if project_obj.has_perm(self.request.user, ProjectPermission.USER):
            return True

        err = 'You do not have permission to view the previous page.'
        messages.error(self.request, err)
        return False

    def return_status_change_records(self, allocations):
        """For the allocations, return the historical record
        that shows when the status was changed to the current status.
        """
        status_change_records = []
        for allocation in allocations:
            # get most recent record with status different from current allocation
            allocation_prechange = allocation.history.filter(
                ~Q(status=allocation.status)
            ).order_by('-history_date').first()
            if allocation_prechange:
                # get history record with same status as current allocation that
                # occurred right after the allocation_prechange entry
                allocation_status_changed = allocation.history.filter(
                    status=allocation.status,
                    history_date__gt=allocation_prechange.history_date,
                ).order_by('history_date').first()
            else:
                allocation_status_changed = allocation.history.last()
            status_change_records.append((allocation, allocation_status_changed))

        return status_change_records

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Can the user update the project?
        context['is_allowed_to_update_project'] = self.object.has_perm(
            self.request.user, ProjectPermission.DATA_MANAGER
        )
        context['is_allowed_to_update_users'] = self.object.has_perm(
            self.request.user, ProjectPermission.ACCESS_MANAGER
        )
        context['is_allowed_to_update_permissions'] = self.object.has_perm(
            self.request.user, ProjectPermission.GENERAL_MANAGER
        )

        if self.request.user.is_superuser:
            attributes = list(
                self.object.projectattribute_set.all().order_by('proj_attr_type__name')
            )
        else:
            attributes = list(
                self.object.projectattribute_set.filter(
                    proj_attr_type__is_private=False
                )
            )

        attributes_with_usage = [
            att for att in attributes if hasattr(att, 'projectattributeusage')
        ]

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(
                    generate_guauge_data_from_usage(
                        attribute.proj_attr_type.name,
                        float(attribute.value),
                        float(attribute.projectattributeusage.value),
                    )
                )
            except ValueError:
                err = "Project attribute '{}' is not an int but has a usage".format(
                    attribute.allocation_attribute_type.name
                )
                logger.error(err)
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        # Only show 'Active Users'
        project_users = self.object.projectuser_set.filter(
                    status__name='Active').order_by('user__username')

        context['mailto'] = 'mailto:' + ','.join([u.user.email for u in project_users])

        allocations = self.object.allocation_set.exclude(status__name='Merged').prefetch_related('resources').order_by('-pk')
        allocation_history_records = self.return_status_change_records(allocations)

        if not self.request.user.is_superuser and not self.request.user.has_perm(
            'allocation.can_view_all_allocations'
        ):
            if self.object.status.name in ['Active', 'New']:
                allocations = allocations.filter(
                    Q(project__projectuser__user=self.request.user)
                )
                # if not self.object.has_perm(self.request.user, ProjectPermission.DATA_MANAGER):
                #     allocations = allocations.filter(
                #         Q(allocationuser__user=self.request.user)
                #     )
        allocations = allocations.filter(
            status__name__in=['Active', 'Paid', 'Ready for Review','Payment Requested']
        ).distinct().order_by('-end_date')
        storage_allocations = allocations.filter(resources__resource_type__name='Storage').order_by('resources__name')
        compute_allocations = allocations.filter(resources__resource_type__name='Cluster')
        allocation_total = {'allocation_user_count': 0, 'size': 0, 'cost': 0, 'usage':0}
        for allocation in storage_allocations:
            if allocation.cost and allocation.requires_payment:
                allocation_total['cost'] += allocation.cost
            if allocation.size:
                allocation_total['size'] += allocation.size
            if allocation.usage:
                allocation_total['usage'] += allocation.usage
            allocation_total['allocation_user_count'] += int(
                allocation.allocationuser_set.count()
            )

        try:
            time_chart_data = generate_usage_history_graph(self.object)
            time_chart_data_error = None
        except Exception as e:
            time_chart_data_error = e
            time_chart_data = '"null"'
        if time_chart_data != '"null"':
            if not time_chart_data['groups'][0]:
                time_chart_data = '"null"'

        if 'django_q' in settings.INSTALLED_APPS:
            # get last successful runs of djangoq task responsible for projectuser data pull
            user_sync_task = Task.objects.filter(
                func__contains="update_group_membership_ldap", success=True
            ).order_by('started').last()
            user_sync_dt = None if not user_sync_task else user_sync_task.started
        else:
            user_sync_dt = None
        context['user_sync_dt'] = user_sync_dt

        context['notes'] = self.return_visible_notes()

        resources = [attr.resource for attr in ResourceAttribute.objects.filter(
            resource_attribute_type__name='Owner',
            value=self.object.title
        )]

        context['resources'] = resources

        context['allocation_history_records'] = allocation_history_records
        context['note_update_link'] = 'project-note-update'
        context['time_chart_data'] = time_chart_data
        context['time_chart_data_error'] = time_chart_data_error
        context['publications'] = Publication.objects.filter(
            project=self.object, status='Active'
        ).order_by('-year')
        context['research_outputs'] = ResearchOutput.objects.filter(
            project=self.object
        ).order_by('-created')
        context['grants'] = Grant.objects.filter(
            project=self.object, status__name__in=['Active', 'Pending', 'Archived']
        )
        context['storage_allocations'] = storage_allocations
        context['compute_allocations'] = compute_allocations
        context['allocation_total'] = allocation_total
        context['attributes'] = attributes
        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['project_users'] = project_users
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        try:
            context['ondemand_url'] = settings.ONDEMAND_URL
        except AttributeError:
            pass
        return context

    def return_visible_notes(self):
        notes = self.object.projectusermessage_set.all()
        if not self.request.user.is_superuser:
            notes = notes.filter(is_private=False)
        return notes


class ProjectListView(ColdfrontListView):
    """ProjectListView"""
    model = Project
    template_name = 'project/project_list.html'
    prefetch_related = ['pi', 'status', 'field_of_science']
    context_object_name = 'item_list'

    def get_queryset(self):
        projects = Project.objects.prefetch_related('pi', 'status').filter(
            status__name__in=['New', 'Active']
        )
        projects_queried = self.search_filters(projects)
        return projects_queried

    def search_filters(self, projects):
        order_by = self.return_order()

        project_search_form = ProjectSearchForm(self.request.GET)
        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if not data.get('show_all_projects') or not (
                self.request.user.is_superuser
                or self.request.user.has_perm('project.can_view_all_projects')
            ):
                projects = projects.filter(
                    Q(projectuser__user=self.request.user)
                    & Q(projectuser__status__name='Active')
                )

            # Last Name
            if data.get('last_name'):
                projects = projects.filter(
                    pi__last_name__icontains=data.get('last_name')
                )

            # Title
            if data.get('title'):
                projects = projects.filter(title__icontains=data.get('title'))

            # Username
            if data.get('username'):
                projects = projects.filter(
                    Q(pi__username__icontains=data.get('username'))
                    | Q(projectuser__user__username__icontains=data.get('username'))
                    & Q(projectuser__status__name='Active')
                )

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get(
                        'field_of_science'
                    )
                )

        else:
            projects = projects.filter(
                Q(projectuser__user=self.request.user)
                & Q(projectuser__status__name='Active')
            )
        return projects.distinct().order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(SearchFormClass=ProjectSearchForm, **kwargs)
        context['expand'] = False
        return context


class ProjectArchivedListView(ProjectListView):
    template_name = 'project/project_archived_list.html'

    def get_queryset(self):
        projects = Project.objects.prefetch_related('pi', 'status').filter(
            status__name__in=['Archived']
        )
        projects_queried = self.search_filters(projects)
        return projects_queried


class ProjectArchiveProjectView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_archive.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        error_message = 'You do not have permission to archive a project.'
        messages.error(self.request, error_message)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        context['project'] = project
        return context

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_status_archive = ProjectStatusChoice.objects.get(name='Archived')
        allocation_status_expired = AllocationStatusChoice.objects.get(name='Expired')
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
    fields = ['title', 'description',]# 'field_of_science']

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        return False

    def form_valid(self, form):
        project_obj = form.save(commit=False)
        try:
            project_create.send(
                sender=self.__class__, project_title=project_obj.title,
            )
        except Exception as exception:
            logger.exception(exception)
            messages.error(self.request, str(exception))
            return HttpResponseRedirect(reverse('project-create'))
        form.instance.status = ProjectStatusChoice.objects.get(name='New')
        form.instance.pi = self.request.user
        try:
            project_obj.save()
        except Exception as exception:
            logger.exception(exception)
            messages.error(
                self.request,
                f"the project could not be created, an error was encountered: {exception}"
            )
            return HttpResponseRedirect(reverse('project-create'))
        form_valid_status = super().form_valid(form)
        try:
            project_post_create.send(
                sender=self.__class__, project_obj=project_obj
            )
        except Exception as exception:
            logger.exception(exception)
            messages.error(
                self.request,
                f"the project was created but an error was encountered in post-creation processes - please contact a system administrator: {exception}"
            )
            return HttpResponseRedirect(reverse('project-create'))
        return form_valid_status

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(
    SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView
):
    model = Project
    template_name_suffix = '_update_form'
    fields = ['title', 'description', 'field_of_science']
    success_message = 'Project updated.'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.DATA_MANAGER):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot update an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})


class ProjectAddUsersSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_add_users.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.ACCESS_MANAGER):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_search_form'] = UserSearchForm()
        context['project'] = Project.objects.get(pk=self.kwargs.get('pk'))
        return context


class ProjectAddUsersSearchResultsView(
    LoginRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = 'project/add_user_search_results.html'
    raise_exception = True

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.ACCESS_MANAGER):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [
            u.user.username
            for u in project_obj.projectuser_set.filter(status__name='Active')
        ]

        combined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude
        )

        context = combined_user_search_obj.search()

        matches = context.get('matches')
        for match in matches:
            match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})

        if matches:
            formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
            formset = formset(initial=matches, prefix='userform')
            context['formset'] = formset
            context['user_search_string'] = user_search_string
            context['search_by'] = search_by

        if len(user_search_string.split()) > 1:
            users_already_in_project = []
            for ele in user_search_string.split():
                if ele in users_to_exclude:
                    users_already_in_project.append(ele)
            context['users_already_in_project'] = users_already_in_project

        # The following block of code is used to hide/show the allocation div in the form.
        if project_obj.allocation_set.filter(
            status__name__in=['Active', 'New', 'Renewal Requested']
        ).exists():
            div_allocation_class = 'placeholder_div_class'
        else:
            div_allocation_class = 'd-none'
        context['div_allocation_class'] = div_allocation_class
        ###

        allocation_form = ProjectAddUsersToAllocationForm(
            request.user, project_obj.pk, prefix='allocationform'
        )
        context['pk'] = pk
        context['allocation_form'] = allocation_form
        return render(request, self.template_name, context)


class ProjectAddUsersView(LoginRequiredMixin, UserPassesTestMixin, View):
    """ProjectAddUsersView"""

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.ACCESS_MANAGER):
            return True
        err = 'You do not have permission to add users to the project.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot add users to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [
            u.user.username
            for u in project_obj.projectuser_set.filter(status__name='Active')
        ]

        combined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude
        )

        context = combined_user_search_obj.search()

        matches = context.get('matches')
        for match in matches:
            match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})

        formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
        formset = formset(request.POST, initial=matches, prefix='userform')

        allocation_form = ProjectAddUsersToAllocationForm(
            request.user, project_obj.pk, request.POST, prefix='allocationform'
        )
        added_users_count = 0

        if formset.is_valid() and allocation_form.is_valid():
            projuserstatus_active = ProjectUserStatusChoice.objects.get(name='Active')
            allocuser_status_active = AllocationUserStatusChoice.objects.get(
                name='Active'
            )
            allocation_form_data = allocation_form.cleaned_data['allocation']
            if '__select_all__' in allocation_form_data:
                allocation_form_data.remove('__select_all__')
            errors = []
            successes = []
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    # Will create local copy of user if not already present in local database
                    # user_obj, _ = get_user_model().objects.update_or_create(
                    #     username=user_form_data.get('username'),
                    #     defaults={
                    #         'first_name': user_form_data.get('first_name'),
                    #         'last_name': user_form_data.get('last_name'),
                    #         'email': user_form_data.get('email'),
                    #     }
                    # )
                    # FASRC Coldfront doesn't add user entries due to internal syncing
                    user_username = user_form_data.get('username')
                    try:
                        user_obj = get_user_model().objects.get(username=user_username)
                    except Exception as e:
                        error = f"Could not locate user for {user_username}: {e}"
                        logger.error('P665: %s', error)
                        errors.append(error)
                        continue

                    role_choice = user_form_data.get('role')

                    try:
                        project_make_projectuser.send(
                            sender=self.__class__,
                            user_name=user_obj.username, group_name=project_obj.title
                        )
                    except Exception as e:
                        error = f"Could not add user {user_obj} to AD Group for {project_obj.title}: {e}\nPlease contact Coldfront administration for further assistance."
                        logger.exception('P646: %s', e)
                        errors.append(error)
                        continue
                    success_msg = f"User {user_obj} added by {request.user} to AD Group for {project_obj.title}"
                    logger.info(success_msg)
                    successes.append(success_msg)

                    # Is the user already in the project?
                    project_obj.projectuser_set.update_or_create(
                        user=user_obj,
                        defaults={
                            'role': role_choice,
                            'status': projuserstatus_active,
                        }
                    )
                    added_users_count += 1
                    for allocation in Allocation.objects.filter(
                        pk__in=allocation_form_data
                    ):
                        if allocation.allocationuser_set.filter(user=user_obj).exists():
                            allocation_user_obj = allocation.allocationuser_set.get(
                                user=user_obj
                            )
                            allocation_user_obj.status = allocuser_status_active
                            allocation_user_obj.save()
                        else:
                            allocation_user_obj = AllocationUser.objects.create(
                                allocation=allocation,
                                user=user_obj,
                                status=allocuser_status_active,
                            )
                        allocation_activate_user.send(
                            sender=self.__class__,
                            allocation_user_pk=allocation_user_obj.pk,
                        )
            if errors:
                for error in errors:
                    messages.error(request, error)

            messages.success(request, f'Added {added_users_count} users to project.')
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
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.ACCESS_MANAGER):
            return True
        err = 'You do not have permission to remove users from the project.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot remove users from an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, project_obj):
        users_to_remove = [
            {
                'username': u.user.username,
                'first_name': u.user.first_name,
                'last_name': u.user.last_name,
                'email': u.user.email,
                'role': u.role,
            }
            for u in project_obj.projectuser_set.filter(status__name='Active').order_by(
                'user__username'
            )
            if u.user not in (self.request.user, project_obj.pi)
        ]
        return users_to_remove

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        users_list = self.get_users_to_remove(project_obj)

        # if ldap is activated, prevent selection of users with project corresponding to primary group
        signal_response = project_filter_users_to_remove.send(
            sender=self.__class__, users_to_remove=users_list, project=project_obj
        )
        if signal_response:
            users_to_remove = signal_response[0][1]
        else:
            users_to_remove = users_list

        users_no_removal = [u for u in users_list if u not in users_to_remove]

        context = {}

        if users_to_remove:
            formset = formset_factory(
                ProjectRemoveUserForm, max_num=len(users_to_remove)
            )
            formset = formset(initial=users_to_remove, prefix='userform')
            context['formset'] = formset

        context['project'] = get_object_or_404(Project, pk=pk)
        context['users_no_removal'] = users_no_removal
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)
        # if ldap is activated, prevent selection of users with project corresponding to primary group
        signal_response = project_filter_users_to_remove.send(
            sender=self.__class__, users_to_remove=users_to_remove, project=project_obj
        )
        if signal_response:
            users_to_remove = signal_response[0][1]
        else:
            users_to_remove = users_to_remove

        formset = formset_factory(ProjectRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(request.POST, initial=users_to_remove, prefix='userform')

        remove_users_count = 0
        failed_user_removals = []

        if formset.is_valid():
            projectuser_status_removed = ProjectUserStatusChoice.objects.get(
                name='Removed'
            )
            allocationuser_status_removed = AllocationUserStatusChoice.objects.get(
                name='Removed'
            )
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    user_obj = get_user_model().objects.get(
                        username=user_form_data.get('username')
                    )
                    if project_obj.pi == user_obj:
                        continue

                    project_user_obj = project_obj.projectuser_set.get(user=user_obj)

                    try:
                        project_preremove_projectuser.send(
                            sender=self.__class__,
                            user_name=user_obj.username, group_name=project_obj.title
                        )
                        logger.info(
                            "P815: Coldfront user %s removed AD User for %s from AD Group for %s",
                            self.request.user,
                            user_obj.username,
                            project_obj.title,
                        )
                    except Exception as e:
                        failed_user_removals += [f"could not remove user {user_obj}: {e}"]
                        logger.exception(
                            "P815: Coldfront user %s could NOT remove AD User for %s from AD Group for %s: %s",
                            self.request.user,
                            user_obj.username,
                            project_obj.title,
                            e
                        )
                        continue

                    project_user_obj.status = projectuser_status_removed
                    project_user_obj.save()

                    # get allocation to remove users from
                    allocations_to_remove_user_from = project_obj.allocation_set.filter(
                        status__name__in=['Active', 'New', 'Renewal Requested'],
                        resources__resource_type__name='Storage'
                    )
                    for allocation in allocations_to_remove_user_from:
                        for alloc_user in allocation.allocationuser_set.filter(
                            user=user_obj, status__name='Active'
                        ):
                            alloc_user.status = allocationuser_status_removed
                            alloc_user.save()

                            allocation_remove_user.send(
                                sender=self.__class__, allocation_user_pk=alloc_user.pk
                            )
                    remove_users_count += 1
            user_pl = 'user' if remove_users_count == 1 else 'users'
            for fail in failed_user_removals:
                messages.error(request, fail)
            messages.success(
                request, f'Removed {remove_users_count} {user_pl} from project.'
            )
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectUserDetail(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_user_detail.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_user = project_obj.projectuser_set.get(pk=self.kwargs.get('project_user_pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.GENERAL_MANAGER):
            if project_user.user == project_obj.pi:
                err = 'You cannot edit the PI of the project.'
                messages.error(self.request, err)
                return False
            else:
                return True
        err = 'You do not have permission to edit project users.'
        messages.error(self.request, err)
        return False

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_user_pk = self.kwargs.get('project_user_pk')

        if project_obj.projectuser_set.filter(pk=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(pk=project_user_pk)

            project_user_update_form = ProjectUserUpdateForm(
                self.request.user, self.kwargs.get('pk'),
                initial={
                    'role': project_user_obj.role,
                    'enable_notifications': project_user_obj.enable_notifications,
                }
            )
            context = {}
            context['project_obj'] = project_obj
            context['project_user_update_form'] = project_user_update_form
            context['project_user_obj'] = project_user_obj

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        project_user_pk = self.kwargs.get('project_user_pk')

        if project_obj.status.name not in ['Active', 'New']:
            messages.error(request, 'You cannot update a user in an archived project.')
            return HttpResponseRedirect(
                reverse('project-user-detail', kwargs={'pk': project_user_pk})
            )

        if project_obj.projectuser_set.filter(id=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(pk=project_user_pk)

            if project_user_obj.user == project_user_obj.project.pi:
                messages.error(
                    request, 'PI role and email notification option cannot be changed.'
                )
                return HttpResponseRedirect(
                    reverse('project-user-detail', kwargs={'pk': project_user_pk})
                )

            project_user_update_form = ProjectUserUpdateForm(
                self.request.user, self.kwargs.get('pk'),
                request.POST,
                initial={
                    'role': project_user_obj.role.name,
                    'enable_notifications': project_user_obj.enable_notifications,
                },
            )

            if project_user_update_form.is_valid():
                form_data = project_user_update_form.cleaned_data
                project_user_obj.enable_notifications = form_data.get(
                    'enable_notifications'
                )
                project_user_obj.role = ProjectUserRoleChoice.objects.get(
                    name=form_data.get('role')
                )
                project_user_obj.save()

                messages.success(request, 'User details updated.')
                return HttpResponseRedirect(
                    reverse(
                        'project-user-detail',
                        kwargs={'pk': pk, 'project_user_pk': project_user_obj.pk},
                    )
                )


@login_required
def project_update_email_notification(request):
    if request.method != 'POST':
        return HttpResponse('no POST', status=400)
    data = request.POST
    project_user_obj = get_object_or_404(ProjectUser, pk=data.get('user_project_id'))

    project_obj = project_user_obj.project

    allowed = False

    if project_obj.has_perm(request.user, ProjectPermission.ACCESS_MANAGER):
        allowed = True
    if project_user_obj.user == request.user:
        allowed = True

    if allowed is False:
        return HttpResponse('not allowed', status=403)

    checked = data.get('checked')
    if checked == 'true':
        project_user_obj.enable_notifications = True
        project_user_obj.save()
        return HttpResponse('checked', status=200)
    if checked == 'false':
        project_user_obj.enable_notifications = False
        project_user_obj.save()
        return HttpResponse('unchecked', status=200)
    return HttpResponse('no checked', status=400)


class ProjectReviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_review.html'
    login_url = '/'  # redirect URL if fail test_func

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.DATA_MANAGER):
            return True
        messages.error(
            self.request, 'You do not have permissions to review this project.'
        )
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        if not project_obj.needs_review:
            messages.error(request, 'You do not need to review this project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))

        err = None
        default_text = 'We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!'

        if 'Auto-Import Project'.lower() in project_obj.title.lower():
            err = 'You must update the project title before reviewing your project. You cannot have "Auto-Import Project" in the title.'
        elif default_text in project_obj.description:
            err = 'You must update the project description before reviewing your project.'

        if err:
            messages.error(request, err)
            return HttpResponseRedirect(reverse('project-update', kwargs={'pk': pk}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_review_form = ProjectReviewForm(project_obj.pk)

        context = {}
        context['project'] = project_obj
        context['project_review_form'] = project_review_form
        context['project_users'] = ', '.join(
            [
                f'{ele.user.first_name} {ele.user.last_name}'
                for ele in project_obj.projectuser_set.filter(
                    status__name='Active'
                ).order_by('user__last_name')
            ]
        )
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        project_review_form = ProjectReviewForm(pk, request.POST)

        project_review_status_choice = ProjectReviewStatusChoice.objects.get(
            name='Pending'
        )

        if not project_review_form.is_valid():
            messages.error(
                request, 'There was an error in processing your project review.'
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
        form_data = project_review_form.cleaned_data
        ProjectReview.objects.create(
            project=project_obj,
            reason_for_not_updating_project=form_data.get('reason'),
            status=project_review_status_choice,
        )

        project_obj.force_review = False
        project_obj.save()

        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('project-review-list'))

        send_email_template(
            'New project review has been submitted',
            'email/new_project_review.txt',
            {'url': url},
            EMAIL_SENDER,
            [EMAIL_DIRECTOR_EMAIL_ADDRESS],
        )

        messages.success(request, 'Project reviewed successfully.')
        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectReviewListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ProjectReview
    template_name = 'project/project_review_list.html'
    prefetch_related = ['project']
    context_object_name = 'project_review_list'

    def get_queryset(self):
        return ProjectReview.objects.filter(status__name='Pending')

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True
        messages.error(
            self.request,
            'You do not have permission to review pending project reviews.',
        )
        return False


class ProjectReviewCompleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True

        err = 'You do not have permission to mark a pending project review as completed.'
        messages.error(self.request, err)
        return False

    def get(self, request, project_review_pk):
        project_review_obj = get_object_or_404(ProjectReview, pk=project_review_pk)
        proj_review_status_completed_obj = ProjectReviewStatusChoice.objects.get(
            name='Completed'
        )
        project_review_obj.status = proj_review_status_completed_obj
        project_review_obj.project.project_needs_review = False
        project_review_obj.save()
        msg = 'Project review for {} has been completed'.format(
            project_review_obj.project.title
        )
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReviewEmailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectReviewEmailForm
    template_name = 'project/project_review_email.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_project_reviews'):
            return True

        err = 'You do not have permission to send email for a pending project review.'
        messages.error(self.request, err)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=self.kwargs.get('pk'))
        context['project_review'] = project_review_obj
        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.kwargs.get('pk'), **self.get_form_kwargs())

    def form_valid(self, form):
        project_review_obj = get_object_or_404(ProjectReview, pk=self.kwargs.get('pk'))
        form_data = form.cleaned_data

        receiver_list = [project_review_obj.project.pi.email]
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
            cc,
        )

        messages.success(
            self.request,
            'Email sent to {} {} ({})'.format(
                project_review_obj.project.pi.first_name,
                project_review_obj.project.pi.last_name,
                project_review_obj.project.pi.username,
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-review-list')


class ProjectNoteCreateView(NoteCreateView):
    model = ProjectUserMessage
    fields = '__all__'
    object_model = Project
    form_obj = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_page'] = 'project-detail'
        context['object_title'] = f'Project {context["object"].title}'
        return context

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('pk')})


class ProjectNoteUpdateView(NoteUpdateView):
    model = ProjectUserMessage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.project
        context['object_detail_link'] = 'project-detail'
        return context

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.project.pk})


class ProjectAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProjectAttribute
    form_class = ProjectAttributeAddForm
    template_name = 'project/project_attribute_create.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        err = 'You do not have permission to add project attributes.'
        messages.error(self.request, err)
        return False

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        initial['project'] = get_object_or_404(Project, pk=pk)
        initial['user'] = self.request.user
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['project'].widget = forms.HiddenInput()
        return form

    def get_context_data(self, *args, **kwargs):
        pk = self.kwargs.get('pk')
        context = super().get_context_data(*args, **kwargs)
        context['project'] = get_object_or_404(Project, pk=pk)
        return context

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project_id})


class ProjectAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = ProjectAttribute
    form_class = ProjectAttributeDeleteForm
    template_name = 'project/project_attribute_delete.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        err = 'You do not have permission to remove project attributes.'
        messages.error(self.request, err)

    def get_avail_attrs(self, project_obj):
        if not self.request.user.is_superuser:
            avail_attrs = ProjectAttribute.objects.filter(
                project=project_obj, proj_attr_type__is_private=False
            )
        else:
            avail_attrs = ProjectAttribute.objects.filter(project=project_obj)
        avail_attrs_dicts = [
            {
                'pk': attr.pk,
                'selected': False,
                'name': str(attr.proj_attr_type),
                'value': attr.value,
            }
            for attr in avail_attrs
        ]
        return avail_attrs_dicts

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        project_attributes_to_delete = self.get_avail_attrs(project_obj)
        context = {}

        if project_attributes_to_delete:
            formset = formset_factory(
                ProjectAttributeDeleteForm, max_num=len(project_attributes_to_delete)
            )
            formset = formset(
                initial=project_attributes_to_delete, prefix='attributeform'
            )
            context['formset'] = formset
        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        attr_to_delete = self.get_avail_attrs(pk)

        formset = formset_factory(
            ProjectAttributeDeleteForm, max_num=len(attr_to_delete)
        )
        formset = formset(request.POST, initial=attr_to_delete, prefix='attributeform')

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:
                    attributes_deleted_count += 1
                    proj_attr = ProjectAttribute.objects.get(pk=form_data['pk'])
                    proj_attr.delete()

            msg = f'Deleted {attributes_deleted_count} attributes from project.'
            messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectAttributeUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_attribute_update.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        err = 'You do not have permission to update project attributes.'
        messages.error(self.request, err)
        return False

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_attribute_pk = self.kwargs.get('project_attribute_pk')

        if project_obj.projectattribute_set.filter(pk=project_attribute_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(
                pk=project_attribute_pk
            )

            project_attribute_update_form = ProjectAttributeUpdateForm(
                initial={
                    'pk': self.kwargs.get('project_attribute_pk'),
                    'name': project_attribute_obj,
                    'value': project_attribute_obj.value,
                    'type': project_attribute_obj.proj_attr_type,
                }
            )
            context = {}
            context['project_obj'] = project_obj
            context['project_attribute_update_form'] = project_attribute_update_form
            context['project_attribute_obj'] = project_attribute_obj
            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        project_attr_pk = self.kwargs.get('project_attribute_pk')

        if project_obj.projectattribute_set.filter(pk=project_attr_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(
                pk=project_attr_pk
            )

            if project_obj.status.name not in ['Active', 'New']:
                err = 'You cannot update an attribute in an archived project.'
                messages.error(request, err)
                return HttpResponseRedirect(
                    reverse(
                        'project-attribute-update',
                        kwargs={'pk': pk, 'project_attribute_pk': project_attr_pk},
                    )
                )

            project_attribute_update_form = ProjectAttributeUpdateForm(
                request.POST, initial={'pk': project_attr_pk}
            )

            if project_attribute_update_form.is_valid():
                form_data = project_attribute_update_form.cleaned_data
                project_attribute_obj.value = form_data.get('new_value')
                project_attribute_obj.save()

                messages.success(request, 'Attribute Updated.')
                return HttpResponseRedirect(
                    reverse('project-detail', kwargs={'pk': pk})
                )
            for error in project_attribute_update_form.errors.values():
                messages.error(request, error)
            return HttpResponseRedirect(
                reverse(
                    'project-attribute-update',
                    kwargs={'pk': pk, 'project_attribute_pk': project_attr_pk},
                )
            )
