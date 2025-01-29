import logging
import requests
from urllib import parse
from django.urls import reverse
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib import messages

from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeType
from coldfront.core.utils.mail import build_link
from coldfront.plugins.slate_project import utils
from coldfront.plugins.slate_project.forms import SlateProjectSearchForm
from coldfront.core.project.models import Project
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from coldfront.plugins.slate_project.forms import SlateProjectForm
from coldfront.plugins.slate_project.utils import check_directory_name_duplicates, check_directory_name_format, get_pi_total_allocated_quantity
from coldfront.core.resource.models import Resource


SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD = import_from_settings('SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD', 120)
SLATE_PROJECT_ENABLE_MOU_SERVER = import_from_settings('SLATE_PROJECT_ENABLE_MOU_SERVER', False)
if SLATE_PROJECT_ENABLE_MOU_SERVER:
    SLATE_PROJECT_MOU_SERVER = import_from_settings('SLATE_PROJECT_MOU_SERVER')
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    SLATE_PROJECT_EMAIL = import_from_settings('SLATE_PROJECT_EMAIL', '')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')

logger = logging.getLogger(__name__)


@login_required
def validate_project_directory_name(request):
    is_valid_format = check_directory_name_format(request.POST.get('directory_name'))
    is_duplicate = check_directory_name_duplicates(request.POST.get('directory_name'))
    message = 'This is a valid Slate Project directory name'
    is_valid = True
    if not is_valid_format:
        message = 'Contains invalid character(s)'
        is_valid = False
    elif is_duplicate:
        message = 'This Slate Project directory name already exists'
        is_valid = False

    context = {
        'is_valid': is_valid,
        'message': message
    }
    
    return render(request, 'slate_project/slate_project_directory_name_validation_results.html', context)


@login_required
def get_slate_project_info(request):
    slate_projects = utils.get_slate_project_info(request.POST.get('viewed_username'))

    context = {
        'slate_projects': slate_projects
    }

    return render(request, 'slate_project/slate_project_info.html', context)

def get_slate_project_estimated_cost(request):
    allocation_obj = Allocation.objects.get(pk=request.POST.get('allocation_pk'))

    estimated_cost = utils.get_estimated_storage_cost(allocation_obj)
    context = {'estimated_cost': estimated_cost}

    return render(request, 'slate_project/estimated_cost.html', context)

def slate_project_search_view(request):
    context = {'form': SlateProjectSearchForm()}
    return render(request, 'slate_project/slate_project_search.html', context)


class SlateProjectSearchResultsView(LoginRequiredMixin, ListView):
    template_name = 'slate_project/slate_project_search_results.html'

    def post(self, request, *args, **kwargs):
        slate_project = request.POST.get('slate_project')
        context = {}
        slate_project_objs = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Slate Project Directory',
            allocation__resources__name='Slate Project',
            allocation__status__name='Active',
            allocation__project__status__name='Active',
            value__icontains='/N/project/' + slate_project
        )
        slate_projects = []
        for slate_project_obj in slate_project_objs:
            allocation_users = slate_project_obj.allocation.allocationuser_set.filter(
                status__name__in=['Active', 'Eligible']).values_list('user', flat=True)

            slate_project = slate_project_obj.value.split('/')[-1]
            slate_projects.append(
                {
                    'slate_project': slate_project_obj,
                    'slate_project_name': slate_project,
                    'allocation_users': allocation_users,
                    'pi': slate_project_obj.allocation.project.pi,
                }
            )

        context['slate_projects'] = slate_projects
        context['EMAIL_ENABLED'] = EMAIL_ENABLED
        return render(request, self.template_name, context)


class RequestAccessEmailView(LoginRequiredMixin, View):

    def post(self, request):
        allocation_obj = get_object_or_404(Allocation, pk=request.POST.get('allocation_pk'))
        project_obj = allocation_obj.project
        if allocation_obj.project.private is True:
            logger.warning(
                f'User {request.user.username} attempted to request access to a slate project '
                f'allocation (allocation pk={allocation_obj.pk}) in a private project'
            )
            return HttpResponseForbidden(reverse('project-list'))

        allocation_url = build_link(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        project_url = build_link(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if EMAIL_ENABLED:
            send_email_template(
                'Add User to Slate Project Request',
                'slate_project/email/slate_project_add_user_request.txt',
                {
                    'center_name': EMAIL_CENTER_NAME,
                    'user': request.user,
                    'project_title': project_obj.title,
                    'project_url': project_url,
                    'slate_project_url': allocation_url,
                    'help_email': SLATE_PROJECT_EMAIL,
                    'signature': EMAIL_SIGNATURE
                },
                EMAIL_TICKET_SYSTEM_ADDRESS,
                [project_obj.pi.email]
            )
            logger.info(
                f'User {request.user.username} sent an email to {project_obj.pi.email} requesting '
                f'access to their slate project allocation (allocation pk={allocation_obj.pk})'
            )
        else:
            logger.warning('Email has not been enabled')
            return HttpResponseForbidden(reverse('project-list'))

        return HttpResponseRedirect(reverse('project-list'))


class SlateProjectView:
    form_class = SlateProjectForm
    template_name = 'slate_project/slateproject.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if not super().test_func():
            return

        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.type.name == 'Class':
            messages.error(self.request, 'Slate Project allocations are not allowed in class projects.')
            return False

        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        pi_username = project_obj.pi.username
        context['total_pi_allocated_quantity'] = utils.get_pi_total_allocated_quantity(pi_username)
        context['pi_allocated_quantity_threshold'] = SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if utils.get_pi_total_allocated_quantity(project_obj.pi.username) + form_data.get('storage_space') <= SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD:
            form.cleaned_data['account_number'] = ''

        if SLATE_PROJECT_ENABLE_MOU_SERVER:
            start_date = form_data.get('start_date', '')
            start_date = start_date.strftime('%m/%d/%Y')

            data = {
                "abstract": form_data.get('description')[:500],
                "campus_affiliation": form_data.get('campus_affiliation', ''),
                "directory_name": form_data.get('project_directory_name', ''),
                "project_title": project_obj.title[:100],
                "project_url": build_link(reverse('project-detail', kwargs={'pk': project_obj.pk})),
                "requested_size_tb": form_data.get('storage_space', ''),
                "requester_email": self.request.user.email,
                "requester_firstname": self.request.user.first_name,
                "requester_lastname": self.request.user.last_name,
                "start_date": start_date,
                "submit_by": self.request.user.username,
                "si": form_data.get('store_ephi', ''),
                "service_type": "Slate-Project",
                "account": form_data.get('account_number', ''),
                "sub_account": '',
                "fiscal_officer": '',
                "faculty_advisor": '',
                "namespace_class": 'RT-PROJ'
            }
            data = parse.urlencode(data)
            try:
                response = requests.post(
                    url=SLATE_PROJECT_MOU_SERVER,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    data=data,
                    timeout=5
                )
                response.raise_for_status()
            except requests.exceptions.Timeout:
                logger.error(f'HTTP error: failed to send data to Slate Project MOU server: Request timed out')
                form.add_error(None, 'Something went wrong processing your request. Please try again later')
                return self.form_invalid(form)
            except requests.HTTPError as http_error:
                logger.error(f'HTTP error: failed to send data to Slate Project MOU server: {http_error}')
                form.add_error(None, 'Something went wrong processing your request. Please try again later')
                return self.form_invalid(form)

        ldap_group = 'condo_' + form_data.get('project_directory_name', '')
        form.cleaned_data['project_directory_name'] = '/N/project/' + form_data.get('project_directory_name', '')

        http_response = super().form_valid(form)

        ldap_group_type = AllocationAttributeType.objects.filter(name='LDAP Group')
        if not ldap_group_type.exists():
            logger.warning('LDAP Group allocation attribute type is missing')
            return http_response

        AllocationAttribute.objects.create(
            allocation=self.allocation_obj,
            allocation_attribute_type=ldap_group_type[0],
            value=ldap_group)
        
        self.allocation_obj.justification = form_data.get('description')
        self.allocation_obj.save()

        return http_response
