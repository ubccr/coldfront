import datetime
from multiprocessing.managers import BaseManager
import pprint
import json
from re import template
from sys import prefix
from typing import Any, List, Optional
from django import http

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import User
from coldfront.core.utils.common import import_from_settings
from django.contrib.messages.views import SuccessMessageMixin
from django.core import serializers
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.forms import formset_factory
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect, JsonResponse)
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user)
from coldfront.core.grant.models import Grant
from coldfront.core.project.forms import (ProjectAddUserForm,
                                          ProjectAddUsersToAllocationForm,
                                          ProjectRemoveUserForm, ProjectRenameForm,
                                          ProjectReviewEmailForm,
                                          ProjectReviewForm, ProjectSearchForm, ProjectSelectForm,
                                          ProjectUserUpdateForm, ProjectImportForm)
from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectReviewStatusChoice,
                                           ProjectStatusChoice, ProjectUser,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice)
from coldfront.core.publication.models import Publication
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.resource.models import Resource
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email, send_email_template

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
        # Can the user update the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif self.object.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.projectuser_set.get(
                user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False

        # Only show 'Active Users'
        project_users = self.object.projectuser_set.filter(
            status__name='Active').order_by('user__username')

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
                                        'Payment Declined', 'Paid','Denied']) &
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


class ProjectListView(LoginRequiredMixin, ListView):

    model = Project
    template_name = 'project/project_list.html'
    prefetch_related = ['pi', 'status', 'field_of_science', ]
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
                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    status__name__in=['New', 'Active', ]).order_by(order_by)
            else:
                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    Q(status__name__in=['New', 'Active', ]) &
                    Q(projectuser__user=self.request.user) &
                    Q(projectuser__status__name='Active')
                ).order_by(order_by)

            # Last Name
            if data.get('last_name'):
                projects = projects.filter(
                    pi__last_name__icontains=data.get('last_name'))

            # Username
            if data.get('username'):
                projects = projects.filter(
                    Q(pi__username__icontains=data.get('username')) |
                    Q(projectuser__user__username__icontains=data.get('username')) &
                    Q(projectuser__status__name='Active')
                )

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get('field_of_science'))

        else:
            projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                Q(status__name__in=['New', 'Active', ]) &
                Q(projectuser__user=self.request.user) &
                Q(projectuser__status__name='Active')
            ).order_by(order_by)

        return projects.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
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
        # project_list = Project.objects.all()
        paginator = Paginator(project_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            project_list = paginator.page(page)
        except PageNotAnInteger:
            project_list = paginator.page(1)
        except EmptyPage:
            project_list = paginator.page(paginator.num_pages)

        return context


class ProjectArchivedListView(LoginRequiredMixin, ListView):

    model = Project
    template_name = 'project/project_archived_list.html'
    prefetch_related = ['pi', 'status', 'field_of_science', ]
    context_object_name = 'project_list'
    paginate_by = 10

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
                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    status__name__in=['Archived', ]).order_by(order_by)
            else:

                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    Q(status__name__in=['Archived', ]) &
                    Q(projectuser__user=self.request.user) &
                    Q(projectuser__status__name='Active')
                ).order_by(order_by)

            # Last Name
            if data.get('last_name'):
                projects = projects.filter(
                    pi__last_name__icontains=data.get('last_name'))

            # Username
            if data.get('username'):
                projects = projects.filter(
                    pi__username__icontains=data.get('username'))

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get('field_of_science'))

        else:
            projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
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


def archive_project(project: Project):
    '''
    Archives the specified project.

    :param project: The project to archive.
    '''
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


class ProjectArchiveProjectView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_archive.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project = get_object_or_404(Project, pk=pk)

        context['project'] = project

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project = get_object_or_404(Project, pk=pk)
        archive_project(project)
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
        form.instance.pi = self.request.user
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
    fields = ['title', 'description', 'field_of_science', ]
    success_message = 'Project updated.'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = self.get_object()

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

def _assign_current_user(self, project_obj: Project):
    '''
    Assigns the current user to the project_obj

    :param self: The self, called from Post
    :param project_obj: The project object to add the user into
    '''
    project_user_obj = ProjectUser.objects.create(
        user=self.request.user,
        project=project_obj,
        role=ProjectUserRoleChoice.objects.get(name='Manager'),
        status=ProjectUserStatusChoice.objects.get(name='Active')
    )

class ProjectMergeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Project
    template_name = 'project/project_merge.html'

    def test_func(self) -> Optional[bool]:
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.is_pi:
            return True

    def get_proj_list(self):

        project_list = [
            {
                'id': project.id,
                'pi': project.pi,
                'title': project.title,
                'description': project.description
            }

            for project in Project.objects.all()
        ]

        return project_list

    def post(self, request, *args, **kwargs):   
        def _combine_objects(from_ids: list, to_id: int, objects: BaseManager):
            '''
            Moves Django models from one project to another. Make sure the model has project_id.

            :param from_ids: A list of ids representing the project to take the models from.
            :param to_id: An id representing the project to give the models to.
            :param objects: The BaseManager for the particular model, to be used to filter from_ids.
            '''
            members = objects.filter(project_id__in = from_ids)
            for member in members:
                member.project_id = to_id
                # member.pk = None      # Uncomment if you want to keep the old projects
                member.save()

        proj_list = self.get_proj_list()
        context = {}

        formset = formset_factory(ProjectSelectForm, max_num=len(proj_list))
        formset = formset(request.POST, initial=proj_list, prefix='projectform')

        projs_to_merge = []
        proj_ids = []

        if formset.is_valid:
            for form in formset:
                proj_form_data = form
                if proj_form_data['selected'].data:
                    proj = Project.objects.get(
                        id = proj_form_data.initial['id']
                    )
                    proj_ids.append(proj_form_data.initial['id'])

                    projs_to_merge.append(proj)
        
        if projs_to_merge:
            merged_proj: Project = Project.objects.create(
                pi = self.request.user,
                status = projs_to_merge[0].status,
                title = request.POST['title'],
                description = request.POST['description'],
            )
            # Title+descript on new page

            # Grants
            _combine_objects(proj_ids, merged_proj.id, Grant.objects)
            
            # Publications
            _combine_objects(proj_ids, merged_proj.id, Publication.objects)

            # User
            # _combine_objects(proj_ids, merged_proj.id, User.objects)

            # Allocations
            old_resource_links: dict = Allocation.objects.filter(project_id__in = proj_ids).values('resources')
            _combine_objects(proj_ids, merged_proj.id, Allocation.objects)

            # Resources
            # Resources are tied to allocations. Since the IDs of allocations are not
            # being changed in merge, resources should remain attached to each allocation.
            # THIS WILL NOT BE THE CASE IF WE DECIDE TO KEEP THE OLD ALLOCATIONS, as the
            # new allocations will change IDs.
            # _combine_objects(proj_ids, merged_proj.id, Resource.objects)

            _assign_current_user(self, merged_proj)

            # Archive all old projects when done. Remove this for loop if you want to
            # keep them.
            for proj in projs_to_merge:
                archive_project(proj)

        return HttpResponseRedirect(reverse('project-list'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        
        proj_list = self.get_proj_list()
        formset = formset_factory(
            ProjectSelectForm, max_num=len(proj_list))
        formset = formset(initial=proj_list, prefix='projectform')
        context['formset'] = formset
        context['projects'] = Project.objects.all()
        context['rename'] = ProjectRenameForm
        return context

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})


class ProjectImportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Project
    template_name = 'project/project_import.html'

    def test_func(self) -> Optional[bool]:
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.is_pi:
            return True

    def post(self, request, *args, **kwargs):
        def _same_obj_exists(cur_obj, new_obj) -> bool:
            '''
            Pass through all fields of cur_obj to see if the deserialized object is
            the same object. If it is, return true, otherwise, return false.
            '''
            cur_vals = model_to_dict(cur_obj)
            new_vals = model_to_dict(new_obj)
            
            unique_keys = []

            for key in cur_obj._meta.fields:
                if key.unique and key.name != 'id':
                    unique_keys.append(key.name)

            for key in unique_keys:
                if cur_vals[key] == new_vals[key]:
                    return True

            # id keys will be updated later in the code
            for key in cur_vals.keys():
                cur_val = cur_vals[key]
                new_val = new_vals[key]

                if key != "id" and cur_val != new_val:
                    return False
            
            return True

        form = ProjectImportForm(request.POST, request.FILES)

        # print(form.is_valid())
        if form.is_valid():
            file = request.FILES['file_upload']
            file_content = file.read()

            grouped_data = {}
            try:
                # The data at this point is grouped and each member needs to be
                # individually feed through the deserializer
                grouped_data = json.loads(file_content)
            except json.JSONDecodeError:
                # Error w/ json decoding
                messages.info(request, "JSON Decode Error: The project file you have selected is corrupted " + 
                    "or is in a format ColdFront does not recognise.")
                return HttpResponseRedirect(reverse('project-list'))
            
            
            # The original project ID. The actual project ID will be changed.
            orig_proj_id = 0

            # Keys are original resource PK, values are the new ones
            resource_trans_nums = {}
            resource_trans_vals = {}

            for member in grouped_data:
                # data_obj has the complete data of the Django model
                data_obj = serializers.deserialize('json', member)  # TODO: Do something with this object

                for obj in data_obj:
                    # obj is deserialized and can now be saved.
                    # Create a new project type
                    if (type(obj.object) == Project):
                        project_obj: Project = obj.object
                        orig_proj_id = int(project_obj.pk)
                        project_obj.pk = None
                        
                        obj.save()

                        # Assign current user.
                        _assign_current_user(self, project_obj)

                        continue
                    
                    orig_pk = obj.object.pk

                    max_pk = 0

                    abort_obj_import = False

                    # Pass through all objects of this type
                    for cur_obj in (type(obj.object)).objects.all():
                        # Put comparison logic here
                        if _same_obj_exists(cur_obj, obj.object):
                            abort_obj_import = True
                            break

                        if cur_obj.pk > max_pk:
                            max_pk = cur_obj.pk

                    if abort_obj_import:
                        continue    # Another same object exists. Abort operation.

                    try:
                        if obj.object.project_id == orig_proj_id:
                            obj.object.project_id = int(project_obj.pk)
                    except AttributeError:
                        pass    # Not all objects have the project id

                    # TESTING
                    try:
                        obj.object.resources.add(resource_trans_vals[1])
                    except AttributeError:
                        pass
                    except KeyError:
                        pass
                            
                    max_pk += 1

                    obj.object.pk = max_pk

                    if (type(obj.object) == Resource):
                        # Create new entry in translation
                        resource_trans_nums[orig_pk] = max_pk
                        resource_trans_vals[orig_pk] = obj.object

                    obj.save()


        return HttpResponseRedirect(reverse('project-list'))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['project_import_form'] = ProjectImportForm()
        return context

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.pk})

def fix_serialize_data(data) -> list:
    # return list([entry for entry in json.loads(serializers.serialize('json', data))])
    return serializers.serialize('json', data)

class ProjectExportView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_export.html'

    def test_func(self) -> Optional[bool]:
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request: http.HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot export an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            serialize_data = [
                fix_serialize_data(Project.objects.filter(pk__exact=self.kwargs.get('pk'))),    # Get current project
                fix_serialize_data(User.objects.all()),
                fix_serialize_data(Publication.objects.all()),
                fix_serialize_data(Grant.objects.all()),
                fix_serialize_data(Resource.objects.all()),
                fix_serialize_data(Allocation.objects.all())
            ]
            response = JsonResponse(serialize_data, content_type='application/json', safe=False, json_dumps_params={'indent': 2})
            response['Content-Disposition'] = 'attachment; filename="project.json"'
            
            return response

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['project'] = Project.objects.get(pk=self.kwargs.get('pk'))
        return context


class ProjectAddUsersSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_add_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

            messages.success(
                request, 'Added {} users to project.'.format(added_users_count))
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

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

            for ele in project_obj.projectuser_set.filter(status__name='Active').order_by('user__username') if ele.user != self.request.user and ele.user != project_obj.pi
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

                    if project_obj.pi == user_obj:
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

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_user_pk = self.kwargs.get('project_user_pk')

        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot update a user in an archived project.')
            return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_user_pk}))

        if project_obj.projectuser_set.filter(id=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(
                pk=project_user_pk)

            if project_user_obj.user == project_user_obj.project.pi:
                messages.error(
                    request, 'PI role and email notification option cannot be changed.')
                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_user_pk}))

            project_user_update_form = ProjectUserUpdateForm(request.POST,
                                                             initial={'role': project_user_obj.role.name,
                                                                      'enable_notifications': project_user_obj.enable_notifications}
                                                             )

            if project_user_update_form.is_valid():
                form_data = project_user_update_form.cleaned_data
                project_user_obj.enable_notifications = form_data.get(
                    'enable_notifications')
                project_user_obj.role = ProjectUserRoleChoice.objects.get(
                    name=form_data.get('role'))
                project_user_obj.save()

                messages.success(request, 'User details updated.')
                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_obj.pk, 'project_user_pk': project_user_obj.pk}))


@login_required
def project_update_email_notification(request):

    if request.method == "POST":
        data = request.POST
        project_user_obj = get_object_or_404(
            ProjectUser, pk=data.get('user_project_id'))


        project_obj = project_user_obj.project

        allowed = False
        if project_obj.pi == request.user:
            allowed = True

        if project_obj.projectuser_set.filter(user=request.user, role__name='Manager', status__name='Active').exists():
            allowed = True

        if project_user_obj.user == request.user:
            allowed = True

        if request.user.is_superuser:
            allowed = True

        if allowed == False:
             return HttpResponse('not allowed', status=403)
        else:
            checked = data.get('checked')
            if checked == 'true':
                project_user_obj.enable_notifications = True
                project_user_obj.save()
                return HttpResponse('checked', status=200)
            elif checked == 'false':
                project_user_obj.enable_notifications = False
                project_user_obj.save()
                return HttpResponse('unchecked', status=200)
            else:
                return HttpResponse('no checked', status=400)
    else:
        return HttpResponse('no POST', status=400)


class ProjectReviewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_review.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
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
            cc
        )

        messages.success(self.request, 'Email sent to {} {} ({})'.format(
            project_review_obj.project.pi.first_name,
            project_review_obj.project.pi.last_name,
            project_review_obj.project.pi.username)
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-review-list')
