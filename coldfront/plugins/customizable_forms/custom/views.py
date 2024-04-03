import logging
import requests

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from coldfront.core.allocation.models import AllocationAttributeType, AllocationAttribute
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.customizable_forms.custom.forms import PositConnectForm, SlateProjectForm
from coldfront.plugins.customizable_forms.views import GenericView

logger = logging.getLogger(__name__)


class PositConnectView(GenericView):
    form_class = PositConnectForm        


class ComputeView(GenericView):
    template_name = 'customizable_forms/generic.html'

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

    def form_valid(self, form):
        http_response = super().form_valid(form)

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        resource_obj =  get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
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
    form_class=SlateProjectForm
    template_name = 'customizable_forms/slateproject.html'

    def form_valid(self, form):
        http_response = super().form_valid(form)

        return http_response