import logging
import requests
from urllib import parse

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from coldfront.core.utils.common import import_from_settings
from coldfront.core.allocation.models import AllocationAttributeType, AllocationAttribute
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.customizable_forms.custom.forms import PositConnectForm, SlateProjectForm, GeodeProjectForm, ComputeForm
from coldfront.plugins.customizable_forms.views import GenericView
from coldfront.plugins.ldap_user_info.utils import get_users_info
from coldfront.plugins.slate_project.utils import get_pi_total_allocated_quantity

logger = logging.getLogger(__name__)


SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD = import_from_settings('SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD', 120)
SLATE_PROJECT_MOU_SERVER = import_from_settings('SLATE_PROJECT_MOU_SERVER', '')


class PositConnectView(GenericView):
    form_class = PositConnectForm        


class ComputeView(GenericView):
    form_class = ComputeForm
    template_name = 'customizable_forms/compute.html'

    def dispatch(self, request, *args, **kwargs):
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        exists = resource_obj.check_user_account_exists(self.request.user.username)
        if not exists:
            messages.error(
                request,
                format_html(
                    f'You do not have an account on {resource_obj.name}. You will need to create '
                    f'one <a href="https://access.iu.edu/Accounts/Create">here</a> in order to '
                    f'submit a resource request for this resource.'
                )
            )
            return HttpResponseRedirect(
                reverse(
                    'custom-allocation-create', kwargs={'project_pk': self.kwargs.get('project_pk')}
                )
            )
        return super().dispatch(request, *args, **kwargs)
    
    def check_user_accounts(self, usernames, resource_obj):
        denied_users = []
        approved_users = []
        results = get_users_info(usernames, ['memberOf'])
        for username in usernames:
            if not resource_obj.check_user_account_exists(username, results.get(username).get('memberOf')):
                denied_users.append(username)
            else:
                approved_users.append(username)

        if denied_users:
            messages.warning(self.request, format_html(
                'The following users do not have an account on {} and were not added: {}. Please\
                direct them to\
                <a href="https://access.iu.edu/Accounts/Create">https://access.iu.edu/Accounts/Create</a>\
                to create an account.'
                .format(resource_obj.name, ', '.join(denied_users))
            ))
        return approved_users

    def form_valid(self, form):
        resource_obj =  get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        usernames = form.cleaned_data.get('users')
        remaining_usernames = self.check_user_accounts(usernames, resource_obj)
        form.cleaned_data['users'] = remaining_usernames
        http_response = super().form_valid(form)

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        slurm_account_allocation_attribute_type_obj = AllocationAttributeType.objects.filter(
            name='slurm_account_name',
            linked_resources__id__exact=resource_obj.id
        )
        if slurm_account_allocation_attribute_type_obj.exists():
            AllocationAttribute.objects.create(
                allocation_attribute_type=slurm_account_allocation_attribute_type_obj[0],
                allocation=self.allocation_obj,
                value=project_obj.slurm_account_name
            )

        return http_response


class SlateProjectView(GenericView):
    form_class = SlateProjectForm
    template_name = 'customizable_forms/slateproject.html'

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        pi_username = project_obj.pi.username
        context['total_pi_allocated_quantity'] = get_pi_total_allocated_quantity(pi_username)
        context['pi_allocated_quantity_threshold'] = SLATE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        start_date = form_data.get('start_date', '')
        start_date = start_date.strftime('%m/%d/%Y')

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        data = {
            "abstract": project_obj.description[:500],
            "campus_affiliation": form_data.get('campus_affiliation', ''),
            "directory_name": form_data.get('project_directory_name', ''),
            "project_title": project_obj.title[:100],
            "project_url": '',
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
            "faculty_advisor": ''
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

        return http_response


class GeodeProjectView(GenericView):
    form_class = GeodeProjectForm
    template_name = 'customizable_forms/geodeproject.html'

    def form_valid(self, form):
        http_response = super().form_valid(form)
        self.allocation_obj.end_date = None
        self.allocation_obj.save()

        return http_response
