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


class RequestHub(LoginRequiredMixin,
                 UserPassesTestMixin,
                 TemplateView):
    template_name = 'request_hub/request_hub.html'
    paginate_by = 2
    paginators = 0

    def get_cluster_account_requests(self):
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

        return cluster_account_list_active, cluster_account_list_complete

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_projectuserremovalrequest'):
            return True
        #
        # message = (
        #     'You do not have permission to review project removal requests.')
        # messages.error(self.request, message)

        return True

    def get_context_data(self, **kwargs):
        def create_paginator(queryset, context_name):
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

            context[context_name] = queryset

            self.paginators += 1

        context = super().get_context_data(**kwargs)

        cluster_account_list_active, cluster_account_list_complete = \
            self.get_cluster_account_requests()

        create_paginator(cluster_account_list_active,
                         'cluster_account_list_active')
        context['num_active_cluster_account_requests'] = len(cluster_account_list_active)

        create_paginator(cluster_account_list_complete,
                         'cluster_account_list_complete')

        return context