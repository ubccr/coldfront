import datetime
import pprint
from itertools import chain

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
from django.utils.html import strip_tags

from coldfront.core.project.models import Project
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.forms import JobSearchForm

from coldfront.core.utils.common import (get_domain_url, import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email, send_email_template

import time

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
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    SUPPORT_EMAIL = import_from_settings('CENTER_HELP_EMAIL')
    EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST')

logger = logging.getLogger(__name__)


class SlurmJobListView(LoginRequiredMixin,
                       ListView):
    template_name = 'job_list.html'
    login_url = '/'
    paginate_by = 30
    context_object_name = 'job_list'

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
            order_by = '-submitdate'

        job_search_form = JobSearchForm(self.request.GET)

        if job_search_form.is_valid():
            data = job_search_form.cleaned_data

            if data.get('show_all_jobs') and (self.request.user.is_superuser or self.request.user.has_perm('statistics.view_job')):
                job_list = Job.objects.all()
            else:
                proj_set = Project.objects.filter(projectuser__user__username=self.request.user, projectuser__status__name__in=['Active', 'Pending - Remove'])
                job_list = Job.objects.filter(Q(accountid__in=proj_set) |
                                              Q(userid=self.request.user))

            if data.get('status'):
                job_list = job_list.filter(jobstatus__icontains=data.get('status'))

            if data.get('jobslurmid'):
                job_list = job_list.filter(jobslurmid__icontains=data.get('jobslurmid'))

            if data.get('project_name'):
                job_list = job_list.filter(accountid__name__icontains=data.get('project_name'))

            if data.get('username'):
                job_list = job_list.filter(userid__username__icontains=data.get('username'))

            if data.get('partition'):
                job_list = job_list.filter(partition__icontains=data.get('partition'))

            if data.get('submitdate'):
                submit_modifier = data.get('submit_modifier')
                submit_date = data.get('submitdate')

                if submit_modifier == 'Before':
                    job_list = job_list.filter(submitdate__lt=submit_date)
                elif submit_modifier == 'On':
                    job_list = job_list.filter(submitdate__year=submit_date.year,
                                               submitdate__month=submit_date.month,
                                               submitdate__day=submit_date.day)
                elif submit_modifier == 'After':
                    job_list = job_list.filter(submitdate__gt=submit_date)

            if data.get('startdate'):
                start_modifier = data.get('start_modifier')
                start_date = data.get('startdate')

                if start_modifier == 'Before':
                    job_list = job_list.filter(startdate__lt=start_date)
                elif start_modifier == 'On':
                    job_list = job_list.filter(startdate__year=start_date.year,
                                               startdate__month=start_date.month,
                                               startdate__day=start_date.day)
                elif start_modifier == 'After':
                    job_list = job_list.filter(startdate__gt=start_date)

            if data.get('enddate'):
                end_modifier = data.get('end_modifier')
                end_date = data.get('enddate')

                if end_modifier == 'Before':
                    job_list = job_list.filter(enddate__lt=end_date)
                elif end_modifier == 'On':
                    job_list = job_list.filter(enddate__year=end_date.year,
                                               enddate__month=end_date.month,
                                               enddate__day=end_date.day)
                elif end_modifier == 'After':
                    job_list = job_list.filter(enddate__gt=end_date)
        else:
            proj_set = Project.objects.filter(projectuser__user__username=self.request.user, projectuser__status__name__in=['Active', 'Pending - Remove'])
            job_list = Job.objects.filter(Q(accountid__in=proj_set) |
                                          Q(userid=self.request.user))

            for error in job_search_form.errors:
                messages.warning(self.request, strip_tags(job_search_form.errors[error]))

        return job_list.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        job_search_form = JobSearchForm(self.request.GET)
        if job_search_form.is_valid():
            context['job_search_form'] = job_search_form
            data = job_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['job_search_form'] = job_search_form
        else:
            filter_parameters = None
            context['job_search_form'] = JobSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        job_list = context['job_list']
        paginator = Paginator(job_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            job_list = paginator.page(page)
        except PageNotAnInteger:
            job_list = paginator.page(1)
        except EmptyPage:
            job_list = paginator.page(paginator.num_pages)

        context['inline_fields'] = ['submitdate', 'submit_modifier',
                                    'startdate', 'start_modifier',
                                    'enddate', 'end_modifier']

        context['status_danger_list'] = ['NODE_FAIL',
                                         'CANCELLED',
                                         'FAILED',
                                         'OUT_OF_MEMORY',
                                         'TIMEOUT']

        context['status_warning_list'] = ['PREEMPTED',
                                          'REQUEUED']

        context['can_view_all_jobs'] = self.request.user.is_superuser or self.request.user.has_perm('statistics.view_job')

        return context


class SlurmJobDetailView(LoginRequiredMixin,
                         UserPassesTestMixin,
                         DetailView):
    model = Job
    template_name = 'job_detail.html'
    context_object_name = 'job'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('statistics.view_job'):
            return True

        job_obj = self.get_object()

        if job_obj.accountid.projectuser_set.filter(
                user=self.request.user,
                status__name__in=['Active', 'Pending - Remove']).exists():
            return True

        messages.error(
            self.request, 'You do not have permission to view the previous page.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_obj = self.get_object()
        context['job'] = job_obj

        context['status_danger_list'] = ['NODE_FAIL',
                                         'CANCELLED',
                                         'FAILED',
                                         'OUT_OF_MEMORY',
                                         'TIMEOUT']

        context['status_warning_list'] = ['PREEMPTED',
                                          'REQUEUED']

        context['nodes'] = ', '.join([x.name for x in job_obj.nodes.all()])

        return context