import datetime
from pipes import Template
import pprint
import django
import logging 

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import User
from coldfront.core.utils.common import import_from_settings
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.forms import formset_factory, modelformset_factory
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from coldfront.core.allocation.utils import generate_guauge_data_from_usage
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserRoleChoice,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user,
                                               allocation_expire)
from coldfront.core.grant.models import Grant
from coldfront.core.project.forms import (ProjectAddUserForm,
                                          ProjectUpdateForm,
                                          ProjectAddUsersToAllocationForm,
                                          ProjectAttributeAddForm,
                                          ProjectAttributeDeleteForm,
                                          ProjectRemoveUserForm,
                                          ProjectReviewEmailForm,
                                          ProjectReviewForm,
                                          ProjectSearchForm,
                                          ProjectUserUpdateForm,
                                          ProjectAttributeUpdateForm,
                                          ProjectRequestEmailForm,
                                          ProjectReviewAllocationForm,
                                          ProjectAddUsersToAllocationFormSet)
from coldfront.core.project.models import (Project,
                                           ProjectAttribute,
                                           ProjectReview,
                                           ProjectReviewStatusChoice,
                                           ProjectStatusChoice,
                                           ProjectUser,
                                           ProjectUserRoleChoice,
                                           ProjectUserStatusChoice,
                                           ProjectUserMessage,
                                           ProjectDescriptionRecord)
from coldfront.core.publication.models import Publication
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email, send_email_template

from django import forms
import urllib
from django.utils.html import format_html
from coldfront.core.user.models import UserProfile
from coldfront.core.project.utils import (get_new_end_date_from_list,
                                          create_admin_action,
                                          get_project_user_emails,
                                          generate_slurm_account_name,
                                          create_admin_action_for_creation,
                                          create_admin_action_for_deletion,
                                          check_if_pi_eligible,
                                          check_if_pis_eligible)
from coldfront.core.allocation.utils import send_added_user_email
from coldfront.core.utils.slack import send_message
from coldfront.core.project.signals import project_activate, project_user_role_changed

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)
PROJECT_DEFAULT_PROJECT_LENGTH = import_from_settings(
    'PROJECT_DEFAULT_PROJECT_LENGTH', 365)
ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING = import_from_settings(
    'ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING', 30)
ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING = import_from_settings(
    'ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING', 60)
PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING', 60)
PROJECT_END_DATE_CARRYOVER_DAYS = import_from_settings(
    'PROJECT_END_DATE_CARRYOVER_DAYS',  90)
PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING', 30)
SLACK_MESSAGING_ENABLED = import_from_settings(
    'SLACK_MESSAGING_ENABLED', False)
ENABLE_SLATE_PROJECT_SEARCH = import_from_settings(
    'ENABLE_SLATE_PROJECT_SEARCH', False)

if EMAIL_ENABLED:
    EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
        'EMAIL_DIRECTOR_EMAIL_ADDRESS')
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_ALERTS_EMAIL_ADDRESS = import_from_settings('EMAIL_ALERTS_EMAIL_ADDRESS')

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

        if project_obj.projectuser_set.filter(user=self.request.user, status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to view the previous page.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        is_manager = False
        # Can the user update the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif self.request.user.has_perm('project.change_project'):
            context['is_allowed_to_update_project'] = True
        elif self.object.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.projectuser_set.get(
                user=self.request.user)
            if project_user.role.name == 'Manager':
                is_manager = True
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False

        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        if self.request.user.is_superuser or self.request.user.has_perm('project.view_projectattribute'):
            attributes_with_usage = [attribute for attribute in project_obj.projectattribute_set.all(
            ).order_by('proj_attr_type__name') if hasattr(attribute, 'projectattributeusage')]

            attributes = [attribute for attribute in project_obj.projectattribute_set.all(
            ).order_by('proj_attr_type__name')]

        else:
            attributes_with_usage = [attribute for attribute in project_obj.projectattribute_set.filter(
                proj_attr_type__is_private=False) if hasattr(attribute, 'projectattributeusage')]

            attributes = [attribute for attribute in project_obj.projectattribute_set.filter(
                proj_attr_type__is_private=False)]

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(generate_guauge_data_from_usage(attribute.proj_attr_type.name,
                                                                  float(attribute.value), float(attribute.projectattributeusage.value)))
            except ValueError:
                logger.error("Allocation attribute '%s' is not an int but has a usage",
                             attribute.allocation_attribute_type.name)
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        # Only show 'Active Users'
        project_users = self.object.projectuser_set.filter(
            status__name__in=['Active', 'Inactive']).order_by('user__username')

        context['mailto'] = 'mailto:' + \
            ','.join([user.user.email for user in project_users])

        if self.request.user.is_superuser or is_manager or self.request.user.has_perm('allocation.can_view_all_allocations'):
            allocations = Allocation.objects.prefetch_related(
                'resources').filter(project=self.object,).order_by('-end_date')

        else:
            allocations = Allocation.objects.filter(
                Q(project=self.object) &
                Q(project__projectuser__user=self.request.user) &
                Q(project__projectuser__status__name__in=['Active', ]) &
                Q(allocationuser__user=self.request.user) &
                Q(allocationuser__status__name__in=['Active', 'Invited', 'Pending', 'Disabled', 'Retired'])
            ).distinct().order_by('-end_date')

        allocation_submitted = self.request.GET.get('allocation_submitted')
        after_project_creation_get = self.request.GET.get('after_project_creation')
        context['display_modal'] = str(allocation_submitted == 'true').lower()
        context['display_project_created_modal'] = str(after_project_creation_get == 'true').lower()
        context['publications'] = Publication.objects.filter(
            project=self.object, status='Active').order_by('-year')
        context['research_outputs'] = ResearchOutput.objects.filter(
            project=self.object).order_by('-created')
        context['grants'] = Grant.objects.filter(
            project=self.object, status__name__in=['Active', 'Pending', 'Archived'])
        context['allocations'] = allocations
        context['attributes'] = attributes
        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['project_users'] = project_users
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        context['PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING'] = PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING
        context['ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING'] = ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING
        context['ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING'] = ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING
        context['enable_customizable_forms'] = 'coldfront.plugins.customizable_forms' in settings.INSTALLED_APPS
        project_messages = project_obj.projectusermessage_set
        if self.request.user.is_superuser or self.request.user.has_perm('project.view_projectusermessage'):
            project_messages = project_messages.all()
        else:
            project_messages = project_messages.filter(is_private=False)
        context['project_messages'] = project_messages.order_by('-created')

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

        order_by = self.request.GET.get('order_by', 'id')
        direction = self.request.GET.get('direction', 'asc')
        if order_by != "name":
            if direction == 'asc':
                direction = ''
            if direction == 'des':
                direction = '-'
            order_by = direction + order_by

        project_search_form = ProjectSearchForm(self.request.GET)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data
            if data.get('show_all_projects') and (self.request.user.is_superuser or self.request.user.has_perm('project.can_view_all_projects')):
                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    status__name__in=['New', 'Active', 'Waiting For Admin Approval', 'Contacted By Admin', 'Review Pending', 'Expired', ]
                ).order_by(order_by)
            else:
                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    Q(status__name__in=['New', 'Active', 'Waiting For Admin Approval', 'Contacted By Admin', 'Review Pending', 'Expired', ]) &
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
            # if data.get('field_of_science'):
            #     projects = projects.filter(
            #         field_of_science__description__icontains=data.get('field_of_science'))

        else:
            projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                Q(status__name__in=['New', 'Active', 'Waiting For Admin Approval', 'Contacted By Admin', 'Review Pending', 'Expired', ]) &
                Q(projectuser__user=self.request.user) &
                Q(projectuser__status__name='Active')
            ).order_by(order_by)

        return projects.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        projects_count = self.get_queryset().count()
        context['projects_count'] = projects_count

        context['enabled_pi_search'] = 'coldfront.plugins.pi_search' in settings.INSTALLED_APPS
        context['enabled_slate_project_search'] = ENABLE_SLATE_PROJECT_SEARCH

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
        context['PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING'] = PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING

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


class ProjectArchivedListView(LoginRequiredMixin, ListView):

    model = Project
    template_name = 'project/project_archived_list.html'
    prefetch_related = ['pi', 'status', 'field_of_science', ]
    context_object_name = 'project_list'
    paginate_by = 10

    def get_queryset(self):

        order_by = self.request.GET.get('order_by', 'id')
        direction = self.request.GET.get('direction', '')
        if order_by != "name":
            if direction == 'des':
                direction = '-'
            order_by = direction + order_by

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
            # if data.get('field_of_science'):
            #     projects = projects.filter(
            #         field_of_science__description__icontains=data.get('field_of_science'))

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


class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Project
    template_name_suffix = '_create_form'
    fields = ['title', 'description', 'pi_username', 'type', 'class_number']

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.is_pi:
            return True

    def get_form(self, form_class = None):
        form = super().get_form(form_class)
        form.fields['pi_username'].required = not check_if_pi_eligible(self.request.user)
        form.fields['description'].widget.attrs.update(
            {
                "placeholder": (
                    "EXAMPLE: Our research involves the collection, storage, and analysis of rat "
                    "colony behaviorial footage to study rat social patterns in natural settings. "
                    "We intend to store the footage in a shared Slate-Project directory, perform "
                    "cleaning of the footage with the Python library Pillow, and then perform "
                    "video classification analysis on the footage using Python libraries such as "
                    "TorchVision using Quartz and Big Red 200."
                )
            }
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pi_search_url'] = ''
        if 'coldfront.plugins.pi_search' in settings.INSTALLED_APPS:
            context['pi_search_url'] = reverse('pi-search-results')

        return context

    def check_max_project_type_count_reached(self, project_obj, pi_obj):
        limit = project_obj.get_env.get('allowed_per_pi')

        if limit is not None:
            pi_projects_count = pi_obj.project_set.filter(
                type=project_obj.type,
                status__name__in=['Active', 'Waiting For Admin Approval', 'Contacted By Admin', 'Review Pending']
            ).count()
            return pi_projects_count >= limit

        return False

    def form_valid(self, form):
        project_obj = form.save(commit=False)
        if not form.instance.pi_username:
            if not check_if_pi_eligible(self.request.user):
                messages.error(self.request, 'Only faculty and staff can be the PI')
                return super().form_invalid(form)
            if self.check_max_project_type_count_reached(form.instance, self.request.user):
                messages.error(
                    self.request, 'You have reached the max projects you can have of this type.'
                )
                return super().form_invalid(form)
            form.instance.pi = self.request.user
        else:
            user = User.objects.filter(username=form.instance.pi_username).first()
            if user is None:
                if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
                    from coldfront.plugins.ldap_user_info.utils import get_user_info
                    result = get_user_info(form.instance.pi_username, ['sAMAccountName'])
                    if not result.get('sAMAccountName')[0]:
                        messages.error(self.request, 'This PI\'s username does not exist.')
                        return super().form_invalid(form)

                messages.error(
                    self.request,
                    f'This PI\'s username could not be found on RT Projects. If they haven\'t yet, '
                    f'they will need to log onto the RT Projects site for their account to be '
                    f'automatically created. Once they do that they can be added as a PI to this '
                    f'project.'
                )
                return super().form_invalid(form)
            if not check_if_pi_eligible(user):
                messages.error(self.request, 'Only faculty and staff can be the PI')
                return super().form_invalid(form)
            if self.check_max_project_type_count_reached(form.instance, user):
                messages.error(
                    self.request,
                    'This PI has reached the max projects they can have of this type.'
                )
                return super().form_invalid(form)
            form.instance.pi = user

        form.instance.requestor = self.request.user
        form.instance.status = ProjectStatusChoice.objects.get(name='Waiting For Admin Approval')

        expiry_dates = project_obj.get_env.get('expiry_dates')
        if expiry_dates:
            full_expire_dates = []
            for date in expiry_dates:
                actual_date = datetime.date(datetime.date.today().year, date[0], date[1])
                full_expire_dates.append(actual_date)
        else:
            full_expire_dates = [datetime.date.today() + datetime.timedelta(days=365)]

        end_date = get_new_end_date_from_list(
            full_expire_dates,
            datetime.date.today(),
            PROJECT_END_DATE_CARRYOVER_DAYS
        )

        if end_date is None:
            logger.error(
                f'End date for new project request was set to None on date {datetime.date.today()}'
            )
            messages.error(
                self.request,
                'Something went wrong while submitting this project request. Please try again later.'
            )
            return super().form_invalid(form)

        project_obj.end_date = end_date

        for field in project_obj.get_env.get('addtl_fields', []):
            if not getattr(form.instance, field):
                messages.error(self.request, f'You must provide a {field} for a {project_obj.type} project.')
                return super().form_invalid(form)

        project_obj.save()
        project_obj.slurm_account_name = generate_slurm_account_name(project_obj)
        project_obj.save()
        self.object = project_obj

        project_user_obj = ProjectUser.objects.create(
            user=self.request.user,
            project=project_obj,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active')
        )
        if form.instance.pi != form.instance.requestor:
            project_user_pi_user = ProjectUser.objects.create(
                user=form.instance.pi,
                project=project_obj,
                role=ProjectUserRoleChoice.objects.get(name='Manager'),
                status=ProjectUserStatusChoice.objects.get(name='Active')
            )

        if SLACK_MESSAGING_ENABLED:
            domain_url = get_domain_url(self.request)
            project_review_url = reverse('project-review-list')
            url = '{}{}'.format(domain_url, project_review_url)
            send_message(
                f'A new request for project "{project_obj.title}" with id {project_obj.pk} has been submitted. You can view it here: {url}')
        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            project_review_url = reverse('project-review-list')
            template_context = {
                'url': '{}{}'.format(domain_url, project_review_url),
                'project_title': project_obj.title,
                'project_id': project_obj.pk
            }
            send_email_template(
                'New Project Request',
                'email/new_project_request.txt',
                template_context,
                EMAIL_SENDER,
                [EMAIL_ALERTS_EMAIL_ADDRESS, ],
            )

            if form.instance.pi != form.instance.requestor:
                project_url = reverse('project-detail', kwargs={'pk': project_obj.pk})
                template_context = {
                    'center_name': EMAIL_CENTER_NAME,
                    'project_title': project_obj.title,
                    'requestor_first_name': form.instance.requestor.first_name,
                    'requestor_last_name': form.instance.requestor.last_name,
                    'requestor_username': form.instance.requestor.username,
                    'project_url': '{}{}'.format(domain_url, project_url),
                    'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                    'signature': EMAIL_SIGNATURE
                }

                send_email_template(
                    'PI For Project Request',
                    'email/pi_project_request.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    [project_user_pi_user.user.email, ]
                )

                logger.info(f'Email sent to pi {form.instance.pi.username} (project pk={project_obj.pk})')

        logger.info(
            f'User {form.instance.requestor.username} created a new project (project pk={project_obj.pk})')
        return super().form_valid(form)

    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)

    def get_success_url(self):
        url_name = 'allocation-create'
        if 'coldfront.plugins.customizable_forms' in settings.INSTALLED_APPS:
            url_name = 'custom-allocation-create'

        return self.reverse_with_params(
            reverse(
                url_name, kwargs={'project_pk': self.object.pk}
            ),
            after_project_creation='true'
        )


class ProjectUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectUpdateForm
    template_name = 'project/project_update_form.html'
    success_message = 'Project updated.'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if self.request.user.has_perm('project.change_project'):
            return True

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name in ['Archived', 'Denied', 'Expired', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot update a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.kwargs.get('pk'), **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_pk'] = self.kwargs.get('pk')

        return context

    def form_valid(self, form):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        form_data = form.cleaned_data

        ProjectDescriptionRecord.objects.create(
            project=project_obj,
            user=self.request.user,
            description=project_obj.description
        )

        save_form = not project_obj.title == form_data.get('title') or not project_obj.description == form_data.get('description')
        project_obj.title = form_data.get('title')
        project_obj.description = form_data.get('description')
        # project_obj.field_of_science = form_data.get('field_of_science')
        if save_form:
            project_obj.save()

        if SLACK_MESSAGING_ENABLED:
            url = f'{get_domain_url(self.request)}{reverse("project-detail", kwargs={"pk": project_obj.pk})}'
            send_message(
                f'Project "{project_obj.title}" with id {project_obj.pk} was updated. You can view '
                f'it here: {url}')
        logger.info(f'User {self.request.user.username} updated a project (project pk={project_obj.pk})')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('pk')})


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
        if project_obj.status.name in ['Archived', 'Denied', 'Expired', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot add users to a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_search_form'] = UserSearchForm()
        context['project'] = Project.objects.get(pk=self.kwargs.get('pk'))
        after_project_creation = self.request.GET.get('after_project_creation')
        context['after_project_creation'] = str(after_project_creation == 'true').lower()
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
        if project_obj.status.name in ['Archived', 'Denied', 'Expired', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot add users to a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_initial_data(self, request, allocations):
        initial_data = []
        for allocation in allocations:
            initial_data.append({
                'pk': allocation.pk,
                'resource': allocation.get_parent_resource.name,
                'resource_type': allocation.get_parent_resource.resource_type.name,
                'status': allocation.status.name
            })

        return initial_data

    def get_allocation_user_roles(self, allocations):
        return [allocation.get_user_roles().values_list('name', flat=True) for allocation in allocations]

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(
            status__name__in=['Active', 'Inactive'])]

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()
        after_project_creation = request.POST.get('after_project_creation')
        context['after_project_creation'] = str(after_project_creation == 'true').lower()

        # Initial data for ProjectAddUserForm
        matches = context.get('matches')
        
        user_accounts = []
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_users_info
            users = [match.get('username') for match in matches]
            results = get_users_info(users, ['title', 'memberOf'])
            for match in matches:
                username = match.get('username')
                user_accounts.append([username, results.get(username).get('memberOf')])

                title = results.get(username).get('title')
                if title and title[0] == 'group':
                    match.update({'role': ProjectUserRoleChoice.objects.get(name='Group')})
                else:
                    match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})
        else:
            for match in matches:
                match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})

        context['user_accounts'] = user_accounts
        context['all_accounts'] = {}

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

        status_list = ['Active', 'New', 'Renewal Requested', 'Billing Information Submitted']
        allocations = project_obj.allocation_set.filter(status__name__in=status_list, is_locked=False).exclude(resources__name='Geode-Project')
        initial_data = self.get_initial_data(request, allocations)
        allocation_formset = formset_factory(
            ProjectAddUsersToAllocationForm,
            max_num=len(initial_data),
            formset=ProjectAddUsersToAllocationFormSet
        )
        roles = self.get_allocation_user_roles(allocations)
        allocation_formset = allocation_formset(
            initial=initial_data,
            prefix="allocationform",
            form_kwargs={'roles': roles}
        )

        resource_accounts = []
        for allocation in allocations:
            resource_obj = allocation.get_parent_resource
            resource_accounts.append([resource_obj.name, resource_obj.get_assigned_account()])

        context['resource_accounts'] = resource_accounts

        # The following block of code is used to hide/show the allocation div in the form.
        if initial_data:
            div_allocation_class = 'placeholder_div_class'
        else:
            div_allocation_class = 'd-none'
        context['div_allocation_class'] = div_allocation_class
        ###

        context['pk'] = pk
        context['allocation_form'] = allocation_formset
        context['current_num_managers'] = project_obj.get_current_num_managers()
        context['max_managers'] = project_obj.max_managers
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
        if project_obj.status.name in ['Archived', 'Denied', 'Expired', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot add users to a project with status "{}".'.format(project_obj.status.name))
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_initial_data(self, request, allocations):
        initial_data = []
        for allocation in allocations:
            initial_data.append({
                'pk': allocation.pk,
                'resource': allocation.get_parent_resource.name,
                'resource_type': allocation.get_parent_resource.resource_type.name,
                'status': allocation.status.name
            })

        return initial_data
    
    def get_users_accounts(self, formset):
        selected_users_accounts = {}
        selected_users_usernames = []
        for form in formset:
            user_form_data = form.cleaned_data
            if user_form_data.get('selected'):
                selected_users_usernames.append(user_form_data.get('username'))
                selected_users_accounts[user_form_data.get('username')] = []

        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_users_info
            results = get_users_info(selected_users_usernames, ['memberOf'])
            for username, result in results.items():
                selected_users_accounts[username] = result.get('memberOf')

        return selected_users_accounts

    def get_allocation_user_roles(self, allocations):
        return [allocation.get_user_roles().values_list('name', flat=True) for allocation in allocations]

    def post(self, request, *args, **kwargs):
        user_search_string = request.POST.get('q')
        search_by = request.POST.get('search_by')
        pk = self.kwargs.get('pk')

        project_obj = get_object_or_404(Project, pk=pk)

        users_to_exclude = [ele.user.username for ele in project_obj.projectuser_set.filter(
            status__name__in=['Active', 'Inactive'])]

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by, users_to_exclude)

        context = cobmined_user_search_obj.search()

        # Initial data for ProjectAddUserForm
        matches = context.get('matches')
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_users_info
            users = [match.get('username') for match in matches]
            results = get_users_info(users, ['title'])
            for match in matches:
                if results.get(match.get('username')).get('title')[0] == 'group':
                    match.update({'role': ProjectUserRoleChoice.objects.get(name='Group')})
                else:
                    match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})
        else:
            for match in matches:
                match.update({'role': ProjectUserRoleChoice.objects.get(name='User')})

        auto_disable_notifications = False
        auto_disable_obj = project_obj.projectattribute_set.filter(
            proj_attr_type__name='Auto Disable User Notifications')
        if auto_disable_obj.exists() and auto_disable_obj[0].value == 'Yes':
            auto_disable_notifications = True

        formset = formset_factory(ProjectAddUserForm, max_num=len(matches))
        formset = formset(request.POST, initial=matches, prefix='userform')

        status_list = ['Active', 'New', 'Renewal Requested', 'Billing Information Submitted']
        allocations = project_obj.allocation_set.filter(status__name__in=status_list, is_locked=False)
        initial_data = self.get_initial_data(request, allocations)

        allocation_formset = formset_factory(
            ProjectAddUsersToAllocationForm,
            max_num=len(initial_data),
            formset=ProjectAddUsersToAllocationFormSet
        )
        roles = self.get_allocation_user_roles(allocations)
        allocation_formset = allocation_formset(
            request.POST,
            initial=initial_data,
            prefix="allocationform",
            form_kwargs={'roles': roles}
        )

        project_user_objs = []
        allocations_added_to = {}
        if formset.is_valid() and allocation_formset.is_valid():
            project_user_active_status_choice = ProjectUserStatusChoice.objects.get(
                name='Active')
            allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active')

            no_accounts = {}
            added_users = {}
            managers_rejected = []
            resources_requiring_user_request = {}
            requestor_user = User.objects.get(username=request.user)
            for allocation in allocation_formset:
                cleaned_data = allocation.cleaned_data
                if cleaned_data['selected']:
                    selected_users_accounts = self.get_users_accounts(formset)
                    break

            for form in formset:
                user_form_data = form.cleaned_data

                if user_form_data['selected']:
                    # Will create local copy of user if not already present in local database
                    user_obj, created = User.objects.get_or_create(
                        username=user_form_data.get('username'))
                    if created:
                        user_obj.first_name = user_form_data.get('first_name')
                        user_obj.last_name = user_form_data.get('last_name')
                        user_obj.email = user_form_data.get('email')
                        user_obj.save()

                    role_choice = user_form_data.get('role')

                    # If no more managers can be added then give the user the 'User' role.
                    if role_choice.name == 'Manager':
                        if project_obj.check_exceeds_max_managers(1):
                            role_choice = ProjectUserRoleChoice.objects.get(name='User')
                            managers_rejected.append(user_form_data.get('username'))

                    enable_notifications = True
                    if role_choice.name == 'Group':
                        # Notifications by default will be disabled for group accounts.
                        enable_notifications = False
                    elif role_choice.name == 'User' and auto_disable_notifications:
                        enable_notifications = False

                    # Is the user already in the project?
                    if project_obj.projectuser_set.filter(user=user_obj).exists():
                        project_user_obj = project_obj.projectuser_set.get(
                            user=user_obj)
                        project_user_obj.role = role_choice
                        project_user_obj.status = project_user_active_status_choice
                        project_user_obj.enable_notifications = enable_notifications
                        project_user_obj.save()
                    else:
                        project_user_obj = ProjectUser.objects.create(
                            user=user_obj,
                            project=project_obj,
                            role=role_choice,
                            status=project_user_active_status_choice,
                            enable_notifications=enable_notifications)

                    project_user_objs.append(project_user_obj)

                    username = user_form_data.get('username')
                    no_accounts[username] = []
                    added_users[username] = []
                    for allocation in allocation_formset:
                        cleaned_data = allocation.cleaned_data
                        if cleaned_data['selected']:
                            allocation = allocations.get(pk=cleaned_data['pk'])
                            if allocations_added_to.get(allocation) is None:
                                allocations_added_to[allocation] = []

                            resource_name = allocation.get_parent_resource.name
                            # If the user does not have an account on the resource in the allocation then do not add them to it.
                            accounts = selected_users_accounts.get(username)
                            account_exists, reason = allocation.get_parent_resource.check_accounts(accounts).values()
                            if not account_exists:
                                # Make sure there are no duplicates for a user if there's more than one instance of a resource.
                                if reason == 'no_account':
                                    if 'IU' not in no_accounts[username]:
                                        no_accounts[username].append('IU')
                                elif reason == 'no_resource_account':
                                    if allocation.get_parent_resource.name not in no_accounts[username]:
                                        no_accounts[username].append(allocation.get_parent_resource.name)
                                continue

                            requires_user_request = allocation.get_parent_resource.get_attribute('requires_user_request')
                            if requires_user_request is not None and requires_user_request == 'Yes':
                                resources_requiring_user_request.setdefault(resource_name, set())
                                resources_requiring_user_request[resource_name].add(username)
                                allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
                                    name='Pending - Add')
                                
                            allocation_user_role_obj = AllocationUserRoleChoice.objects.filter(
                                resources=allocation.get_parent_resource, name=cleaned_data['role'])
                            if allocation_user_role_obj.exists():
                                allocation_user_role_obj = allocation_user_role_obj[0]
                            else:
                                allocation_user_role_obj = None

                            if allocation.allocationuser_set.filter(user=user_obj).exists():
                                allocation_user_obj = allocation.allocationuser_set.get(
                                    user=user_obj)
                                allocation_user_obj.status = allocation_user_status_choice
                                allocation_user_obj.role = allocation_user_role_obj
                                allocation_user_obj.save()
                            else:
                                allocation_user_obj = AllocationUser.objects.create(
                                    allocation=allocation,
                                    user=user_obj,
                                    role=allocation_user_role_obj,
                                    status=allocation_user_status_choice)

                            allocation_activate_user.send(sender=self.__class__,
                                                        allocation_user_pk=allocation_user_obj.pk)

                            requires_user_request = allocation.get_parent_resource.get_attribute(
                                'requires_user_request')

                            allocation_user_request_obj = allocation.create_user_request(
                                requestor_user=requestor_user,
                                allocation_user=allocation_user_obj,
                                allocation_user_status=allocation_user_status_choice

                            )

                            if allocation_user_request_obj is None:
                                allocations_added_to[allocation].append(project_user_obj)

                            if allocation.get_parent_resource.name not in added_users[username]:
                                added_users[username].append(allocation.get_parent_resource.name)

            if any(no_accounts.values()):
                warning_message = 'The following users were not added to the selected resource allocations due to missing accounts:<ul>'
                for username, no_account_list in no_accounts.items():
                    if no_account_list:
                        if 'IU' in no_account_list:
                            warning_message += f'<li>{username} is missing an IU account</li>'
                        else:
                            warning_message += f'<li>{username} is missing an account for {", ".join(no_account_list)}</li>'
                warning_message += '</ul>'
                if warning_message != '':
                    url = 'https://access.iu.edu/Accounts/Create'
                    warning_message += f'They cannot be added until they create one. Please direct them to <a href="{url}">{url}</a> to create one.'
                    messages.warning(request, format_html(warning_message))

            if any(added_users.values()):
                message = 'The following users were added to the selected resource allocations:<ul>'
                for username, resource_list in added_users.items():
                    if resource_list:
                        message += f'<li>{username} was added to these resource allocations: {", ".join(resource_list)}</li>'
                message += '</ul>'
                messages.success(request, format_html(message))

            if EMAIL_ENABLED and project_user_objs:
                domain_url = get_domain_url(self.request)
                project_url = '{}{}'.format(domain_url, reverse(
                    'project-detail', kwargs={'pk': project_obj.pk}))

                template_context = {
                    'center_name': EMAIL_CENTER_NAME,
                    'project_title': project_obj.title,
                    'project_users': project_user_objs,
                    'url': project_url,
                    'signature': EMAIL_SIGNATURE
                }
                emails = [project_user_obj.user.email for project_user_obj in project_user_objs if project_user_obj.enable_notifications]
                emails.append(project_obj.pi.email)
                send_email_template(
                    'Added to Project', 'email/project_added_users.txt', template_context, EMAIL_TICKET_SYSTEM_ADDRESS, emails)

                if allocations_added_to:
                    for allocation, added_project_user_objs in allocations_added_to.items():
                        if allocation.status.name == 'New':
                            continue
                        users = [project_user_obj.user for project_user_obj in added_project_user_objs if project_user_obj.enable_notifications]
                        emails = [user.email for user in users]
                        if emails and project_obj.pi.email not in emails:
                            emails.append(project_obj.pi.email)

                            send_added_user_email(
                                request, allocation, users, emails)

            if project_user_objs:
                logger.info(
                    f'User {request.user.username} added {", ".join(project_user_obj.user.username for project_user_obj in project_user_objs)} '
                    f'to a project (project pk={project_obj.pk})'
                )
            if allocations_added_to:
                for allocation, added_project_user_objs in allocations_added_to.items():
                    project_users = [project_user_obj.user.username for project_user_obj in added_project_user_objs]
                    if project_users:
                        logger.info(
                            f'User {request.user.username} added {", ".join(project_users)} to a '
                            f'{allocation.get_parent_resource.name} allocation (allocation pk={allocation.pk})'
                        )
            messages.success(
                request, 'Added {} users to project.'.format(len(project_user_objs)))
        else:
            if not formset.is_valid():
                for error in formset.errors:
                    messages.error(request, error)

            if not allocation_formset.is_valid():
                for error in allocation_formset.errors:
                    messages.error(request, error)

        if request.POST.get('after_project_creation') == 'true':
            return HttpResponseRedirect(
                self.reverse_with_params(
                    reverse('project-detail', kwargs={'pk': pk}), after_project_creation='true')
            )

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))
    
    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)


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
        if project_obj.status.name in ['Archived', 'Denied', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot remove users from a project with status "{}".'.format(project_obj.status.name))
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

            for ele in project_obj.projectuser_set.filter(status__name__in=['Active', 'Inactive']).order_by('user__username') if ele.user != self.request.user and ele.user != project_obj.pi
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

        project_obj = get_object_or_404(Project, pk=pk)
        context['project'] = project_obj
        context['display_warning'] = project_obj.allocation_set.filter(resources__name='Slate-Project')
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove = self.get_users_to_remove(project_obj)

        formset = formset_factory(
            ProjectRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(
            request.POST, initial=users_to_remove, prefix='userform')

        removed_user_objs = []
        if formset.is_valid():
            project_user_removed_status_choice = ProjectUserStatusChoice.objects.get(
                name='Removed')
            allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(
                name='Removed')
            resources_requiring_user_request = {}
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    if project_obj.pi == user_obj:
                        continue

                    remove_user_from_project = True

                    # get allocation to remove users from
                    allocations_to_remove_user_from = project_obj.allocation_set.filter(
                        status__name__in=['Active', 'New', 'Renewal Requested', 'Expired'])
                    for allocation in allocations_to_remove_user_from:
                        for allocation_user_obj in allocation.allocationuser_set.filter(user=user_obj).exclude(status__name='Removed'):
                            resource = allocation.get_parent_resource
                            requires_user_requests = resource.get_attribute('requires_user_request')

                            # Users will still be removed from allocations that do not require a
                            # user review.
                            if requires_user_requests is not None and requires_user_requests == 'Yes':
                                resources_requiring_user_request.setdefault(resource.name, set())
                                resources_requiring_user_request[resource.name].add(
                                    allocation_user_obj.user.username)
                                remove_user_from_project = False
                                continue

                            allocation_user_obj.status = allocation_user_removed_status_choice
                            allocation_user_obj.save()

                            allocation_remove_user.send(sender=self.__class__,
                                                        allocation_user_pk=allocation_user_obj.pk)

                    if remove_user_from_project:
                        project_user_obj = project_obj.projectuser_set.get(
                            user=user_obj)
                        project_user_obj.status = project_user_removed_status_choice
                        project_user_obj.save()
                        removed_user_objs.append(project_user_obj)

            if removed_user_objs:
                if EMAIL_ENABLED:
                    emails = [project_user_obj.user.email for project_user_obj in removed_user_objs if project_user_obj.enable_notifications]
                    emails.append(project_obj.pi.email)

                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'project_title': project_obj.title,
                        'removed_users': removed_user_objs,
                        'signature': EMAIL_SIGNATURE
                    }
                    send_email_template(
                        'Removed From Project',
                        'email/project_removed_users.txt',
                        template_context,
                        EMAIL_TICKET_SYSTEM_ADDRESS,
                        emails
                    )

                removed_users = [project_user_obj.user.username for project_user_obj in removed_user_objs]
                logger.info(
                    f'User {request.user.username} removed {", ".join(removed_users)} from a '
                    f'project (project pk={project_obj.pk})'
                )

                removed_user_count = len(removed_user_objs)
                if removed_user_count == 1:
                    messages.success(
                        request, 'Removed {} user from project.'.format(removed_user_count))
                else:
                    messages.success(
                        request, 'Removed {} users from project.'.format(removed_user_count))

            for resource_name, users in resources_requiring_user_request.items():
                messages.warning(
                    request, 'User(s) {} in resource {} must be removed from the allocation first.'
                    .format(', '.join(users), resource_name)
                )
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

        if project_obj.status.name in ['Archived', 'Denied', 'Expired', 'Renewal Denied', ]:
            messages.error(
                request, 'You cannot update a user in a(n) {} project.'.format(project_obj.status.name))
            return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_user_pk}))

        if project_obj.projectuser_set.filter(id=project_user_pk).exists():
            project_user_obj = project_obj.projectuser_set.get(
                pk=project_user_pk)

            if project_user_obj.user == project_user_obj.project.pi:
                messages.error(
                    request, 'PI role and email notification option cannot be changed.')
                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_user_pk}))
            project_user_update_form = ProjectUserUpdateForm(
                request.POST,
                initial={
                    'role': project_user_obj.role.name,
                    'enable_notifications': project_user_obj.enable_notifications
                }
            )

            if project_user_update_form.is_valid():
                form_data = project_user_update_form.cleaned_data
                form_role = form_data.get('role')
                form_enable_notifications = form_data.get('enable_notifications')

                if (form_role == project_user_obj.role and 
                    project_user_obj.enable_notifications == form_enable_notifications):
                    return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_obj.pk, 'project_user_pk': project_user_obj.pk})) 

                if form_role.name == 'Manager':
                    if project_user_obj.role.name != 'Manager':
                        if project_obj.get_current_num_managers() >= project_obj.max_managers:
                            messages.error(
                                request,
                                """
                                This project is at its maximum Managers limit ({}) and cannot have
                                more.
                                """.format(project_obj.max_managers)
                            )
                            return HttpResponseRedirect(
                                reverse(
                                    'project-user-detail',
                                    kwargs={
                                        'pk': project_obj.pk,
                                        'project_user_pk': project_user_obj.pk
                                    }
                                )
                            )

                old_role = project_user_obj.role
                project_user_obj.role = form_role
                if project_user_obj.role.name == 'Manager':
                    project_user_obj.enable_notifications = True
                elif old_role.name == 'Manager' and project_user_obj.role.name == 'User':
                    auto_disable_obj = project_obj.projectattribute_set.filter(
                        proj_attr_type__name='Auto Disable User Notifications')
                    if auto_disable_obj.exists() and auto_disable_obj[0].value == 'Yes':
                        project_user_obj.enable_notifications = False
                    else:
                        project_user_obj.enable_notifications = True
                else:
                    project_user_obj.enable_notifications = form_enable_notifications
                    logger.info(
                        f'Admin {request.user.username} set {project_user_obj.user.username}\'s '
                        f'notifications to {form_enable_notifications} (project pk={project_obj.pk})'
                    )
                project_user_obj.save()

                if project_user_obj.role != old_role:
                    project_user_role_changed.send(sender=self.__class__, project_user_pk=project_user_obj.pk)
                    logger.info(
                        f'User {request.user.username} changed {project_user_obj.user.username}\'s '
                        f'role to {form_data.get("role")} (project pk={project_obj.pk})'
                    )

                messages.success(request, 'User details updated.')
                return HttpResponseRedirect(reverse('project-user-detail', kwargs={'pk': project_obj.pk, 'project_user_pk': project_user_obj.pk}))
            else:
                messages.error(request, project_user_update_form.errors)
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

        if allowed is False:
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

        if not project_obj.needs_review and not project_obj.can_be_reviewed:
            if project_obj.get_env.get('renewable'):
                messages.error(request, 'You do not need to review this project.')
            else:
                messages.error(request, 'This project cannot be reviewed.')
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

    def get_allocation_data(self, project_obj):
        allocations = project_obj.allocation_set.filter(
            status__name__in=['Active', 'Expired', ],
            is_locked=False,
            resources__requires_payment=False
        )
        initial_data = []
        if allocations:
            for allocation in allocations:
                if ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING >= 0 and allocation.expires_in < -ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING:
                    continue

                data = {
                    'pk': allocation.pk,
                    'resource': allocation.get_resources_as_string,
                    'users': ', '.join(
                        [
                            '{} {}'.format(
                                ele.user.first_name, ele.user.last_name
                            ) for ele in allocation.allocationuser_set.filter(
                                status__name__in=['Active', 'Inactive', 'Invited', 'Pending', 'Disabled', 'Retired']
                            ).order_by('user__last_name')
                        ]
                    ),
                    'status': allocation.status,
                    'expires_on': allocation.end_date,
                    'renew': True
                }
                initial_data.append(data)

        return initial_data

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_review_form = ProjectReviewForm()

        context = {}
        context['project'] = project_obj
        context['project_review_form'] = project_review_form
        context['project_users'] = ', '.join(['{} {}'.format(ele.user.first_name, ele.user.last_name)
                                              for ele in project_obj.projectuser_set.filter(status__name__in=['Active','Inactive']).order_by('user__last_name')])
        context['ineligible_pi'] = not check_if_pi_eligible(project_obj.pi)
        context['formset'] = []
        allocation_data = self.get_allocation_data(project_obj)
        if allocation_data:
            formset = formset_factory(ProjectReviewAllocationForm, max_num=len(allocation_data))
            formset = formset(initial=allocation_data, prefix='allocationform')
            context['formset'] = formset

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_review_form = ProjectReviewForm(request.POST)

        project_review_status_choice = ProjectReviewStatusChoice.objects.get(
            name='Pending')
        project_status_choice = ProjectStatusChoice.objects.get(name="Review Pending")

        allocation_renewals = []
        if project_review_form.is_valid():
            allocation_data = self.get_allocation_data(project_obj)
            if allocation_data:
                formset = formset_factory(ProjectReviewAllocationForm, max_num=len(allocation_data))
                formset = formset(request.POST, initial=allocation_data, prefix='allocationform')

                if formset.is_valid():
                    allocation_status_choice = AllocationStatusChoice.objects.get(name="Renewal Requested")
                    for form in formset:
                        data = form.cleaned_data
                        if data.get('renew'):
                            allocation_renewals.append(str(data.get('pk')))
                            allocation = Allocation.objects.get(pk=data.get('pk'))
                            allocation.status = allocation_status_choice
                            allocation.save()
                else:
                    logger.error(
                        f'There was an error submitting allocation renewals for PI '
                        f'{project_obj.pi.username} (project pk={project_obj.pk})'
                        f'Errors: {formset.errors}'
                    )

                    messages.error(
                        request, 'There was an error submitting your allocation renewals.'
                    )
                    return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

            form_data = project_review_form.cleaned_data
            project_updates = form_data.get('project_updates')
            if form_data.get('no_project_updates'):
                project_updates = 'No new project updates.'

            project_review_obj = ProjectReview.objects.create(
                project=project_obj,
                project_updates=project_updates,
                allocation_renewals=','.join(allocation_renewals),
                status=project_review_status_choice)

            project_obj.force_review = False
            project_obj.status = project_status_choice
            project_obj.save()

            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse('project-review-list'))

            if EMAIL_ENABLED:
                send_email_template(
                    'New project renewal has been submitted',
                    'email/new_project_renewal.txt',
                    {
                        'url': url,
                        'project_title': project_obj.title,
                        'project_id': project_obj.pk
                    },
                    EMAIL_SENDER,
                    [EMAIL_ALERTS_EMAIL_ADDRESS, ]
                )

            if SLACK_MESSAGING_ENABLED:
                domain_url = get_domain_url(self.request)
                project_review_url = reverse('project-review-list')
                url = '{}{}'.format(domain_url, project_review_url)
                text = (
                    f'A new renewal request for project "{project_obj.title}" with id '
                    f'{project_obj.pk} has been submitted. You can view it here: {url}'
                )
                send_message(text)

            logger.info(
                f'User {request.user.username} submitted a project review (project pk={project_obj.pk})'
            )

            messages.success(request, 'Project review submitted.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            messages.error(
                request, 'There was an error in processing your project review.')

            errors = project_review_form.errors.get('__all__')
            if errors and len(errors):
                for error in errors:
                    messages.error(request, error)

            return HttpResponseRedirect(reverse('project-review', kwargs={'pk': project_obj.pk}))


class ProjectReviewListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_review_list.html'
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_projects'):
            return True

        messages.error(
            self.request, 'You do not have permission to review pending project reviews/requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project_reviews = ProjectReview.objects.filter(
            status__name__in=['Pending', 'Contacted By Admin', ]).order_by('created')
        pi_eligibilities = check_if_pis_eligible(
            set([project_review.project.pi for project_review in project_reviews]))
        context['project_review_list'] = project_reviews
        context['pi_eligibilities'] = pi_eligibilities

        projects = Project.objects.filter(
            status__name__in=['Waiting For Admin Approval', 'Contacted By Admin', ]
        ).order_by('created')
        context['project_request_list'] = projects

        pis = set([project.pi for project in projects])
        pis = pis.union(set([project_review.project.pi for project_review in project_reviews]))
        pi_project_objs = Project.objects.filter(
            Q(
                pi__in=pis,
                status__name__in=[
                    'Active', 'Waiting For Admin Approval', 'Contacted By Admin', 'Review Pending'
                ],
            ) |
            Q(
                pi__in=pis,
                status__name='Expired',
                end_date__gt=datetime.datetime.now() - datetime.timedelta(days=PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING)
            )
        ).order_by('status__name')
        pi_projects = []
        for pi_project_obj in pi_project_objs:
            pi_projects.append(
                {
                    'pk': pi_project_obj.pk,
                    'title': pi_project_obj.title,
                    'pi': pi_project_obj.pi.username,
                    'description': pi_project_obj.description,
                    'status': pi_project_obj.status.name,
                    'display': 'false' 
                }
            )
        context['pi_projects'] = pi_projects

        context['EMAIL_ENABLED'] = EMAIL_ENABLED
        return context


class ProjectReviewCompleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Currently not in use."""
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_projects'):
            return True

        messages.error(
            self.request, 'You do not have permission to mark a pending project review as completed.')

    def get(self, request, project_review_pk):
        project_review_obj = get_object_or_404(
            ProjectReview, pk=project_review_pk)

        project_review_status_completed_obj = ProjectReviewStatusChoice.objects.get(
            name='Completed')
        project_review_obj.status = project_review_status_completed_obj
        if project_review_obj.project.project_needs_review:
            project_review_obj.project.project_needs_review = False
            project_review_obj.save()

        messages.success(request, 'Project review for {} has been completed'.format(
            project_review_obj.project.title)
        )

        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReviewEmailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectReviewEmailForm
    template_name = 'project/project_review_email.html'
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not EMAIL_ENABLED:
            messages.error(
                self.request, 'Emails are not enabled.')
            return False

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_projects'):
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
        return form_class(self.kwargs.get('pk'), self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        form_data = form.cleaned_data

        project_review_status_obj = ProjectReviewStatusChoice.objects.get(name='Contacted By Admin')
        project_review_obj.status = project_review_status_obj
        project_review_obj.save()

        receiver_list = [project_review_obj.project.pi.email]
        cc = form_data.get('cc').strip()
        if cc:
            cc = cc.split(',')
        else:
            cc = []

        send_email(
            f'Follow-up on Renewal for Project {project_review_obj.project.title}',
            form_data.get('email_body'),
            EMAIL_TICKET_SYSTEM_ADDRESS,
            receiver_list,
            cc
        )
        success_text = 'Email sent to {} {} ({}).'.format(
            project_review_obj.project.pi.first_name,
            project_review_obj.project.pi.last_name,
            project_review_obj.project.pi.username
        )
        if cc:
            success_text += ' CCed: {}'.format(', '.join(cc))

        messages.success(self.request, success_text)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-review-list')



class ProjectNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProjectUserMessage
    fields = '__all__'
    template_name = 'project/project_note_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to add project notes.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        context['project'] = project_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        author = self.request.user
        initial['project'] = project_obj
        initial['author'] = author
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['project'].widget = forms.HiddenInput()
        form.fields['author'].widget = forms.HiddenInput()
        form.order_fields([ 'project', 'author', 'message', 'is_private' ])
        return form

    def get_success_url(self):
        logger.info(
            f'Admin {self.request.user.username} created a project attribute (pk={self.kwargs.get("pk")})')
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('pk')})

class ProjectAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProjectAttribute
    form_class = ProjectAttributeAddForm
    template_name = 'project/project_attribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        user = self.request.user
        if user.is_superuser or user.has_perm('project.add_projectattribute'):
            return True

        messages.error(
            self.request, 'You do not have permission to add project attributes.')

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
        logger.info(
            f'Admin {self.request.user.username} created a project attribute (project pk={self.object.project_id})')
        create_admin_action_for_creation(
            self.request.user,
            self.object,
            get_object_or_404(Project, pk=self.object.project_id)
        )
        return reverse('project-detail', kwargs={'pk': self.object.project_id})


class ProjectAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = ProjectAttribute
    form_class = ProjectAttributeDeleteForm
    template_name = 'project/project_attribute_delete.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        user = self.request.user
        if user.is_superuser or user.has_perm('project.delete_projectattribute'):
            return True

        messages.error(
            self.request, 'You do not have permission to add project attributes.')

    def get_avail_attrs(self, project_obj):
        if not self.request.user.is_superuser and not self.request.user.has_perm('project.delete_projectattribute'):
            avail_attrs = ProjectAttribute.objects.filter(project=project_obj, proj_attr_type__is_private=False)
        else:
            avail_attrs = ProjectAttribute.objects.filter(project=project_obj)
        avail_attrs_dicts = [
            {
                'pk' : attr.pk,
                'selected' : False,
                'name' : str(attr.proj_attr_type),
                'value' : attr.value
            }

            for attr in avail_attrs
        ]

        return avail_attrs_dicts

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        project_attributes_to_delete = self.get_avail_attrs(
            project_obj)
        context = {}

        if project_attributes_to_delete:
            formset = formset_factory(ProjectAttributeDeleteForm, max_num=len(
                project_attributes_to_delete))
            formset = formset(
                initial=project_attributes_to_delete, prefix='attributeform')
            context['formset'] = formset
        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        attr_to_delete = self.get_avail_attrs(pk)

        formset = formset_factory(
            ProjectAttributeDeleteForm,
            max_num=len(attr_to_delete)
            )
        formset = formset(
            request.POST,
            initial=attr_to_delete,
            prefix='attributeform'
            )

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:
                    attributes_deleted_count += 1

                    proj_attr = ProjectAttribute.objects.get(
                        pk=form_data['pk'])

                    proj_attr.delete()

                    create_admin_action_for_deletion(
                        self.request.user,
                        proj_attr,
                        get_object_or_404(Project, pk=pk)
                    )

            logger.info(
                f'Admin {self.request.user.username} deleted {attributes_deleted_count} project '
                f'attributes (project pk={pk})'
            )

            messages.success(request, 'Deleted {} attributes from project.'.format(
                attributes_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))

class ProjectAttributeUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_attribute_update.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        user = self.request.user
        if user.is_superuser or user.has_perm('project.change_projectattribute'):
            return True

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_attribute_pk = self.kwargs.get('project_attribute_pk')
       

        if project_obj.projectattribute_set.filter(pk=project_attribute_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(
                pk=project_attribute_pk)

            project_attribute_update_form = ProjectAttributeUpdateForm(
                initial={'pk': self.kwargs.get('project_attribute_pk'),'name': project_attribute_obj, 'value': project_attribute_obj.value, 'type' : project_attribute_obj.proj_attr_type})

            context = {}
            context['project_obj'] = project_obj
            context['project_attribute_update_form'] = project_attribute_update_form
            context['project_attribute_obj'] = project_attribute_obj

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project_attribute_pk = self.kwargs.get('project_attribute_pk')

        if project_obj.projectattribute_set.filter(pk=project_attribute_pk).exists():
            project_attribute_obj = project_obj.projectattribute_set.get(
                pk=project_attribute_pk)

            if project_obj.status.name not in ['Active', 'New', 'Waiting For Admin Approval', 'Contacted By Admin', 'Renewal Requested']:
                messages.error(
                    request, f'You cannot update an attribute in a project with status {project_obj.status.name}.')
                return HttpResponseRedirect(reverse('project-attribute-update', kwargs={'pk': project_obj.pk, 'project_attribute_pk': project_attribute_obj.pk}))

            project_attribute_update_form = ProjectAttributeUpdateForm(request.POST, initial={'pk': self.kwargs.get('project_attribute_pk'),})

            if project_attribute_update_form.is_valid():
                form_data = project_attribute_update_form.cleaned_data
                logger.info(
                    f'Admin {request.user.username} updated a project attribute (project pk={project_obj.pk})')
                create_admin_action(
                    request.user,
                    {'value': form_data.get('new_value')},
                    project_obj,
                    project_attribute_obj
                )
                project_attribute_obj.value = form_data.get(
                     'new_value')
                project_attribute_obj.save()

                messages.success(request, 'Attribute Updated.')
                return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
            else:
                for error in project_attribute_update_form.errors.values():
                    messages.error(request, error)
                return HttpResponseRedirect(reverse('project-attribute-update', kwargs={'pk': project_obj.pk, 'project_attribute_pk': project_attribute_obj.pk}))

class ProjectDeniedListView(LoginRequiredMixin, ListView):

    model = Project
    template_name = 'project/project_denied_list.html'
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
                    status__name__in=['Denied', 'Renewal Denied', ]).order_by(order_by)
            else:

                projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                    Q(status__name__in=['Denied', 'Renewal Denied', ]) &
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
            # if data.get('field_of_science'):
            #     projects = projects.filter(
            #         field_of_science__description__icontains=data.get('field_of_science'))

        else:
            projects = Project.objects.prefetch_related('pi', 'field_of_science', 'status',).filter(
                Q(status__name__in=['Denied', 'Renewal Denied', ]) &
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

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name in ['Denied', 'Waiting For Admin Approval', 'Review Pending', 'Contacted By Admin', 'Renewal Denied', ]:
            messages.error(
                request,
                'You cannot archive a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project = get_object_or_404(Project, pk=pk)

        context['project'] = project

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
        project.end_date = end_date
        project.save()
        for allocation in project.allocation_set.filter(status__name='Active'):
            allocation.status = allocation_status_expired
            allocation.end_date = end_date
            allocation.save()

            allocation_expire.send(sender=ProjectArchiveProjectView, allocation_pk=allocation.pk)

        logger.info(
            f'User {request.user.username} archived a project (project pk={project.pk})'
        )
        return redirect(reverse('project-detail', kwargs={'pk': project.pk}))


class ProjectActivateRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not self.request.user.is_superuser:
            if not self.request.user.has_perm('project.can_review_pending_projects'):
                return False

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Waiting For Admin Approval', 'Contacted By Admin', ]:
            messages.error(
                self.request, f'You cannot approve a project with status "{project_obj.status.name}"'
            )
            return False

        return True

    def get(self, request, pk):
        project_obj = get_object_or_404(Project, pk=pk)
        project_status_obj = ProjectStatusChoice.objects.get(name="Active")

        create_admin_action(request.user, {'status': project_status_obj}, project_obj)

        project_obj.status = project_status_obj
        project_obj.save()

        project_activate.send(sender=self.__class__, project_pk=project_obj.pk)
        messages.success(request, 'Project request for {} has been APPROVED'.format(
            project_obj.title))

        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            project_url = '{}{}'.format(domain_url, reverse(
                'project-detail', kwargs={'pk': project_obj.pk}
            ))

            template_context = {
                'project_title': project_obj.title,
                'project_url': project_url,
                'signature': EMAIL_SIGNATURE,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'center_name': EMAIL_CENTER_NAME
            }

            email_receiver_list = get_project_user_emails(project_obj)
            send_email_template(
                'Your Project Request Was Approved',
                'email/project_request_approved.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} approved a project request (project pk={project_obj.pk})'
        )
        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectDenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not self.request.user.is_superuser:
            if not self.request.user.has_perm('project.can_review_pending_projects'):
                return False

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Waiting For Admin Approval', 'Contacted By Admin', ]:
            messages.error(
                self.request, f'You cannot deny a project with status "{project_obj.status.name}"'
            )
            return False

        return True

    def get(self, request, pk):
        project_obj = get_object_or_404(Project, pk=pk)
        project_status_obj = ProjectStatusChoice.objects.get(name="Denied")

        create_admin_action(request.user, {'status': project_status_obj}, project_obj)

        project_obj.status = project_status_obj

        free_allocation_obj_list = project_obj.allocation_set.filter(status__name__in=['Active', 'New', 'Renewal Requested'])
        allocation_status_obj = AllocationStatusChoice.objects.get(name="Denied")
        for allocation in free_allocation_obj_list:
            allocation.status = allocation_status_obj
            allocation.save()

        paid_allocation_obj_list = project_obj.allocation_set.filter(status__name__in=['Payment Requested', 'Payment Pending', 'Paid'])
        allocation_status_obj = AllocationStatusChoice.objects.get(name="Payment Declined")
        for allocation in paid_allocation_obj_list:
            allocation.status = allocation_status_obj
            allocation.save()

        project_obj.save()

        messages.success(request, 'Project request for {} has been DENIED'.format(
            project_obj.title))

        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            project_url = '{}{}'.format(domain_url, reverse(
                'project-detail', kwargs={'pk': project_obj.pk}
            ))

            template_context = {
                'project_title': project_obj.title,
                'project_url': project_url,
                'signature': EMAIL_SIGNATURE,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'center_name': EMAIL_CENTER_NAME
            }

            email_receiver_list = get_project_user_emails(project_obj, True)
            
            send_email_template(
                'Your Project Request Was Denied',
                'email/project_request_denied.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} denied a project request (project pk={project_obj.pk})'
        )
        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReviewApproveView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not self.request.user.is_superuser:
            if not self.request.user.has_perm('project.can_review_pending_projects'):
                return False

        project_review_obj = get_object_or_404(ProjectReview, pk=self.kwargs.get('pk'))
        if project_review_obj.status.name not in ['Pending', 'Contacted By Admin', ]:
            messages.error(
                self.request, f'You cannot approve a project review with status "{project_review_obj.status.name}"'
            )
            return False

        return True

    def get(self, request, pk):
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        project_review_status_obj = ProjectReviewStatusChoice.objects.get(name="Approved")
        project_obj = project_review_obj.project
        project_status_obj = ProjectStatusChoice.objects.get(name="Active")

        expiry_dates = project_obj.get_env.get('expiry_dates')
        if expiry_dates:
            full_expire_dates = []
            for date in expiry_dates:
                actual_date = datetime.date(datetime.date.today().year, date[0], date[1])
                full_expire_dates.append(actual_date)
        else:
            full_expire_dates = [datetime.date.today() + datetime.timedelta(days=365)]

        end_date = get_new_end_date_from_list(
            full_expire_dates,
            datetime.date.today(),
            PROJECT_END_DATE_CARRYOVER_DAYS
        )

        if end_date is None:
            logger.error(
                f'New end date for project {project_obj.title} was set to None with project '
                f'review creation date {project_review_obj.created.date()} during project '
                f'review approval'
            )
            messages.error(request, 'Something went wrong while approving the review.')
            return HttpResponseRedirect(reverse('project-review-list'))

        project_obj.end_date = end_date

        create_admin_action(request.user, {'status': project_status_obj}, project_obj)

        project_review_obj.status = project_review_status_obj
        project_obj.status = project_status_obj
        project_review_obj.save()
        project_obj.save()

        messages.success(request, 'Project review for {} has been APPROVED'.format(
            project_review_obj.project.title)
        )

        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            project_url = '{}{}'.format(domain_url, reverse(
                'project-detail', kwargs={'pk': project_review_obj.project.pk}
            ))

            template_context = {
                'project_title': project_review_obj.project.title,
                'project_url': project_url,
                'signature': EMAIL_SIGNATURE,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'center_name': EMAIL_CENTER_NAME,
            }

            email_receiver_list = get_project_user_emails(project_obj)
            send_email_template(
                'Your Project Renewal Was Approved',
                'email/project_renewal_approved.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} approved a project renewal request (project pk={project_obj.pk})'
        )
        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReviewDenyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not self.request.user.is_superuser:
            if not self.request.user.has_perm('project.can_review_pending_projects'):
                return False

        project_review_obj = get_object_or_404(ProjectReview, pk=self.kwargs.get('pk'))
        if project_review_obj.status.name not in ['Pending', 'Contacted By Admin', ]:
            messages.error(
                self.request, f'You cannot deny a project review with status "{project_review_obj.status.name}"'
            )
            return False

        return True

    def get(self, request, pk):
        project_review_obj = get_object_or_404(ProjectReview, pk=pk)
        project_review_status_obj = ProjectReviewStatusChoice.objects.get(name="Denied")
        project_obj = project_review_obj.project
        project_status_obj = ProjectStatusChoice.objects.get(name="Renewal Denied")

        create_admin_action(request.user, {'status': project_status_obj}, project_obj)

        project_review_obj.status = project_review_status_obj
        project_obj.status = project_status_obj

        allocation_renewals = project_obj.allocation_set.filter(status__name='Renewal Requested')
        if allocation_renewals:
            allocation_active_status_choice = AllocationStatusChoice.objects.get(name="Active")
            allocation_expired_status_choice = AllocationStatusChoice.objects.get(name="Expired")
            for allocation in allocation_renewals:
                if allocation.end_date < datetime.datetime.now().date():
                    allocation.status = allocation_expired_status_choice
                    allocation_expire.send(sender=ProjectReviewDenyView, allocation_pk=allocation.pk)
                else:
                    allocation.status = allocation_active_status_choice
                allocation.save()

        project_review_obj.save()
        project_obj.save()

        messages.success(request, 'Project review for {} has been DENIED'.format(
            project_review_obj.project.title)
        )

        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            project_url = '{}{}'.format(domain_url, reverse(
                'project-detail', kwargs={'pk': project_review_obj.project.pk}
            ))
            not_renewed_allocation_urls = []
            if project_review_obj.allocation_renewals:
                for allocation_pk in project_review_obj.allocation_renewals.split(','):
                    allocation_url = '{}{}'.format(domain_url, reverse(
                        'allocation-detail', kwargs={'pk': allocation_pk}
                    ))
                    not_renewed_allocation_urls.append(allocation_url)

            template_context = {
                'project_title': project_review_obj.project.title,
                'project_url': project_url,
                'signature': EMAIL_SIGNATURE,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'center_name': EMAIL_CENTER_NAME,
                'not_renewed_allocation_urls': not_renewed_allocation_urls,
                'signature': EMAIL_SIGNATURE
            }

            email_receiver_list = get_project_user_emails(project_obj, True)
            send_email_template(
                'Your Project Renewal Was Denied',
                'email/project_renewal_denied.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} denied a project renewal request (project pk={project_obj.pk})'
        )
        return HttpResponseRedirect(reverse('project-review-list'))


class ProjectReviewInfoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_review_info.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not self.request.user.is_superuser:
            if not self.request.user.has_perm('project.can_review_pending_projects'):
                return False

        project_review_obj = get_object_or_404(ProjectReview, pk=self.kwargs.get('pk'))
        if project_review_obj.status.name not in ['Pending', 'Contacted By Admin']:
            messages.error(
                self.request, f'You cannot view a project review\'s info with status "{project_review_obj.status.name}"'
            )
            return False

        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        context['project_review'] = get_object_or_404(ProjectReview, pk=pk)

        return context


class ProjectRequestEmailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectRequestEmailForm
    template_name = 'project/project_request_email.html'
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not EMAIL_ENABLED:
            messages.error(
                self.request, 'Emails are not enabled.')
            return False

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.can_review_pending_projects'):
            return True

        messages.error(
            self.request, 'You do not have permission to send email for a pending project request.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        context['project'] = project_obj

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.kwargs.get('pk'), self.request.user, **self.get_form_kwargs())

    def form_valid(self, form):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        form_data = form.cleaned_data

        project_status_obj = ProjectStatusChoice.objects.get(name='Contacted By Admin')
        create_admin_action(self.request.user, {'status': project_status_obj}, project_obj)

        project_obj.status = project_status_obj
        project_obj.save()

        if EMAIL_ENABLED:
            receiver_list = [project_obj.requestor.email]
            cc = form_data.get('cc').strip()
            if cc:
                cc = cc.split(',')
            else:
                cc = []

            send_email(
                f'Follow-up on Project {project_obj.title}',
                form_data.get('email_body'),
                EMAIL_TICKET_SYSTEM_ADDRESS,
                receiver_list,
                cc
            )

            success_text = 'Email sent to {} {} ({}).'.format(
                project_obj.requestor.first_name,
                project_obj.requestor.last_name,
                project_obj.requestor.username
            )
            if cc:
                success_text += ' CCed: {}'.format(', '.join(cc))

            messages.success(self.request, success_text)
        else:
            messages.error(self.request, 'Failed to send email: Email not enabled')

            logger.warning(
                'Email has not been enabled'
            )
            return super().form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-review-list')


class ProjectRequestAccessEmailView(LoginRequiredMixin, View):

    def post(self, request):
        project_obj = get_object_or_404(Project, pk=request.POST.get('project_pk'))
        if project_obj.private is True:
            logger.warning(
                "User {} attempted to request access to a private project (pk={})".format(
                    request.user.username,
                    project_obj.pk
                )
            )
            return HttpResponseForbidden(reverse('project-list'))

        domain_url = get_domain_url(self.request)
        project_url = '{}{}'.format(domain_url, reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if EMAIL_ENABLED:
            send_email_template(
                'Add User to Project Request',
                'email/project_add_user_request.txt',
                {
                    'center_name': EMAIL_CENTER_NAME,
                    'user': request.user,
                    'project_title': project_obj.title,
                    'project_url': project_url,
                    'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                    'signature': EMAIL_SIGNATURE
                },
                EMAIL_TICKET_SYSTEM_ADDRESS,
                [project_obj.pi.email]
            )
            logger.info(
                f'User {request.user.username} sent an email to {project_obj.pi.email} requesting '
                f'access to their project (project pk={project_obj.pk})'
            )
        else:
            logger.warning(
                'Email has not been enabled'
            )
            return HttpResponseForbidden(reverse('project-list'))

        return HttpResponseRedirect(reverse('project-list'))
