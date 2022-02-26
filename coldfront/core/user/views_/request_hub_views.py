from itertools import chain

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttributeType,
                                              AllocationUserStatusChoice,
                                              AllocationUserAttribute)

from coldfront.core.project.forms_.removal_forms import \
    (ProjectRemovalRequestSearchForm,
     ProjectRemovalRequestUpdateStatusForm,
     ProjectRemovalRequestCompletionForm)
from coldfront.core.project.models import (Project,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice,
                                           SavioProjectAllocationRequest)
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email_template

import logging

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)

if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    SUPPORT_EMAIL = import_from_settings('CENTER_HELP_EMAIL')

logger = logging.getLogger(__name__)


class RequestListItem:
    def __init__(self):
        num = None
        title = None
        num_active = None
        list_template = None
        active_queryset = None
        complete_queryset = None
        button_path = None
        button_text = None


class RequestHub(LoginRequiredMixin,
                 TemplateView):
    template_name = 'request_hub/request_hub.html'
    paginate_by = 5
    paginators = 0
    show_all_requests = False

    def create_paginator(self, queryset):
        """
        Creates a paginator object for the given queryset
        and updates the context with the created object.
        """
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get(f'page{self.paginators}')
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = paginator.page(paginator.num_pages)

        self.paginators += 1

        return queryset

    def get_cluster_account_request(self):
        """Populates a RequestListItem with data for cluster account requests"""
        cluster_request_object = RequestListItem()

        user = self.request.user

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        kwargs = {'allocation_user__user': user,
                  'allocation_attribute_type': cluster_account_status}

        cluster_account_list_complete = AllocationUserAttribute.objects.filter(
            value__in=['Denied', 'Active'], **kwargs)

        cluster_account_list_active = AllocationUserAttribute.objects.filter(
            value__in=['Pending - Add', 'Processing'], **kwargs)

        cluster_request_object.num = self.paginators
        cluster_request_object.active_queryset = \
            self.create_paginator(cluster_account_list_active)

        cluster_request_object.complete_queryset = \
            self.create_paginator(cluster_account_list_complete)

        cluster_request_object.num_active = cluster_account_list_active.count()

        cluster_request_object.title = 'Cluster Account Requests'
        cluster_request_object.list_template = \
            'request_hub/cluster_account_list.html'
        cluster_request_object.button_path = \
            'allocation-cluster-account-request-list'
        cluster_request_object.button_text = \
            'Go To Cluster Account Requests Main Page'

        return cluster_request_object

    def get_project_removal_request(self):
        """Populates a RequestListItem with data for project removal requests"""
        removal_request_object = RequestListItem()
        user = self.request.user

        args = [Q(project_user__user=user) | Q(requester=user)]

        removal_request_active = ProjectUserRemovalRequest.objects.filter(
            status__name__in=['Pending', 'Processing'], *args)

        removal_request_complete = ProjectUserRemovalRequest.objects.filter(
            status__name='Complete', *args)

        removal_request_object.num = self.paginators
        removal_request_object.active_queryset = \
            self.create_paginator(removal_request_active)

        removal_request_object.complete_queryset = \
            self.create_paginator(removal_request_complete)

        removal_request_object.num_active = removal_request_active.count()

        removal_request_object.title = 'Project Removal Requests'
        removal_request_object.list_template = \
            'request_hub/removal_request_list.html'
        removal_request_object.button_path = \
            'project-removal-request-list'
        removal_request_object.button_text = \
            'Go To Project Removal Requests Main Page'

        return removal_request_object

    def get_savio_project_request(self):
        """Populates a RequestListItem with data for savio project requests"""
        savio_proj_request_object = RequestListItem()
        user = self.request.user

        args = [Q(pi=user) | Q(requester=user)]

        project_request_active = SavioProjectAllocationRequest.objects.filter(
            status__name__in=['Under Review', 'Approved - Processing'], *args)

        project_request_complete = SavioProjectAllocationRequest.objects.filter(
            status__name__in=['Approved - Complete', 'Denied'], *args)

        savio_proj_request_object.num = self.paginators
        savio_proj_request_object.active_queryset = \
            self.create_paginator(project_request_active)

        savio_proj_request_object.complete_queryset = \
            self.create_paginator(project_request_complete)

        savio_proj_request_object.num_active = project_request_active.count()

        savio_proj_request_object.title = 'Savio Project Requests'
        savio_proj_request_object.list_template = \
            'request_hub/savio_project_request_list.html'
        savio_proj_request_object.button_path = \
            'savio-project-pending-request-list'
        savio_proj_request_object.button_text = \
            'Go To Savio Project Requests Main Page'

        return savio_proj_request_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        requests = ['cluster_account_request',
                    'project_removal_request',
                    'savio_project_request']

        for request in requests:
            context[f'{request}_obj'] = eval(f'self.get_{request}()')

        context['show_all'] = (self.request.user.is_superuser or
                               self.request.user.is_staff) and \
                              self.show_all_requests

        return context
