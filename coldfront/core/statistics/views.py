import copy
import csv
import itertools
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.utils.html import strip_tags

from coldfront.core.project.models import Project
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.forms import JobSearchForm

import logging

from coldfront.core.statistics.utils_.job_query_filtering import \
    job_query_filtering
from coldfront.core.utils.common import Echo

logger = logging.getLogger(__name__)
DATE_FORMAT = '%m/%d/%Y, %H:%M:%S'


class SlurmJobListView(LoginRequiredMixin,
                       ListView):
    template_name = 'job_list.html'
    login_url = '/'
    paginate_by = 30
    context_object_name = 'job_list'

    def save_form_to_session(self, data):
        new_data = copy.deepcopy(data)
        for date in ['submitdate', 'startdate', 'enddate']:
            if data.get(date, None):
                new_data[date] = data.get(date, None).strftime(DATE_FORMAT)
        self.request.session['job_search_form_data'] = new_data
        self.request.session.modified = True

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

        job_search_form = JobSearchForm(self.request.GET, user=self.request.user)

        if job_search_form.is_valid():
            data = job_search_form.cleaned_data
            self.save_form_to_session(data)

            if data.get('show_all_jobs') and \
                    (self.request.user.is_superuser or
                     self.request.user.has_perm('statistics.view_job')):
                job_list = Job.objects.all()
            else:
                proj_set = Project.objects.filter(
                    projectuser__user__username=self.request.user,
                    projectuser__status__name__in=['Active', 'Pending - Remove'],
                    projectuser__role__name__in=['Principal Investigator', 'Manager'])
                job_list = Job.objects.filter(Q(accountid__in=proj_set) |
                                              Q(userid=self.request.user))

            job_list = job_query_filtering(job_list, data)

        else:
            job_list = Job.objects.none()

            for error in job_search_form.errors:
                messages.warning(self.request,
                                 strip_tags(job_search_form.errors[error]))

        return job_list.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        job_search_form = JobSearchForm(self.request.GET, user=self.request.user)
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
                                              'order_by=%s&direction=%s&' % \
                                              (order_by, direction)
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

        context['can_view_all_jobs'] = \
            self.request.user.is_superuser or \
            self.request.user.has_perm('statistics.view_job')

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
                status__name__in=['Active', 'Pending - Remove'],
                role__name__in=['Principal Investigator', 'Manager']).exists():
            return True

        if job_obj.userid == self.request.user:
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


class ExportJobListView(LoginRequiredMixin,
                        UserPassesTestMixin,
                        View):

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

    def dispatch(self, request, *args, **kwargs):
        if self.test_func():
            data = copy.deepcopy(self.request.session.get('job_search_form_data'))

            job_list = Job.objects.all()

            if data:
                for date in ['submitdate', 'startdate', 'enddate']:
                    if data.get(date, None):
                        data[date] = \
                            datetime.strptime(data.get(date, None), DATE_FORMAT)
                job_list = job_query_filtering(job_list, data)

            echo_buffer = Echo()
            writer = csv.writer(echo_buffer)
            header = ('jobslurmid',
                      'username',
                      'project_name',
                      'partition',
                      'jobstatus',
                      'submitdate',
                      'startdate',
                      'enddate',
                      'service_units')
            job_list = job_list.values_list('jobslurmid',
                                            'userid__username',
                                            'accountid__name',
                                            'partition',
                                            'jobstatus',
                                            'submitdate',
                                            'startdate',
                                            'enddate',
                                            'amount')
            rows = (writer.writerow(row) for row in itertools.chain([header], job_list.iterator()))
            response = StreamingHttpResponse(rows, content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="job_list.csv"'

            return response
        else:
            return super().dispatch(request, *args, **kwargs)
