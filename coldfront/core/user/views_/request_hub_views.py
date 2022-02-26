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
                                           ProjectUserRemovalRequestStatusChoice)
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
    cur_num = 0

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
        cluster_request_object = RequestListItem()

        user = self.request.user

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        cluster_account_list_complete = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=cluster_account_status,
            value__in=['Denied', 'Active'],
            allocation_user__user=user)

        cluster_account_list_active = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=cluster_account_status,
            value__in=['Pending - Add', 'Processing'],
            allocation_user__user=user)

        cluster_request_object.active_queryset = \
            self.create_paginator(cluster_account_list_active)

        cluster_request_object.complete_queryset = \
            self.create_paginator(cluster_account_list_complete)

        cluster_request_object.num_active = cluster_account_list_active.count()

        cluster_request_object.title = 'Cluster Account Requests'
        cluster_request_object.list_template = 'request_hub/cluster_account_list.html'
        cluster_request_object.button_path = 'allocation-cluster-account-request-list'
        cluster_request_object.button_text = 'Go To Cluster Account Requests Main Page'
        cluster_request_object.num = self.cur_num
        self.cur_num += 2

        return cluster_request_object

    # def get_project_removal_requests(self, context):
    #     user = self.request.user
    #
    #     project_user_cond = Q(project_user__user=user)
    #     requester_cond = Q(requester=user)
    #
    #     removal_request_active = ProjectUserRemovalRequest.objects.filter(
    #         status__name__in=['Pending', 'Processing']).\
    #         filter(project_user_cond | requester_cond)
    #
    #     removal_request_complete = ProjectUserRemovalRequest.objects.filter(
    #         status__name='Complete').\
    #         filter(project_user_cond | requester_cond)
    #
    #     context = self.create_paginator(removal_request_active,
    #                                     context,
    #                                     'removal_request_active')
    #
    #     context = self.create_paginator(removal_request_complete,
    #                                     context,
    #                                     'removal_request_complete')
    #
    #     context['num_active_removal_request'] = \
    #         removal_request_active.count()
    #
    #     return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        requests = ['cluster_account_request',]
                    # 'project_removal_request']

        for request in requests:
            context[f'{request}_obj'] = eval(f'self.get_{request}()')

        context['show_all'] = (self.request.user.is_superuser or
                               self.request.user.is_staff) and \
                              self.show_all_requests

        return context
