import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db import transaction
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.base import TemplateView

from flags.state import flag_enabled

from coldfront.core.project.forms import JoinRequestSearchForm
from coldfront.core.project.forms import ProjectReviewUserJoinForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import send_project_join_request_denial_email
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource


logger = logging.getLogger(__name__)


class ProjectReviewJoinRequestsView(LoginRequiredMixin, UserPassesTestMixin,
                                    TemplateView):
    form_class = ProjectReviewUserJoinForm
    template_name = 'project/project_review_join_requests.html'

    project_obj = None
    redirect = None
    users_to_review = []

    def test_func(self):
        return (
            self._is_superuser_or_project_owner() or
            self.request.user.has_perm('project.can_view_all_projects'))

    def dispatch(self, request, *args, **kwargs):
        self.project_obj = get_object_or_404(
            Project.objects.prefetch_related('projectuser_set'),
            pk=self.kwargs.get('pk'))
        self.redirect = HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': self.project_obj.pk}))
        if self.project_obj.status.name not in ['Active', 'New', ]:
            message = 'You cannot review join requests to an archived project.'
            messages.error(request, message)
            return self.redirect
        self.users_to_review = self._get_users_to_review()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {}

        users_to_review = self.users_to_review
        if users_to_review:
            formset = formset_factory(
                self.form_class, max_num=len(users_to_review))
            formset = formset(initial=users_to_review, prefix='userform')
            context['formset'] = formset

        context['project'] = self.project_obj

        context['can_add_users'] = self._is_superuser_or_project_owner()

        if flag_enabled('LRC_ONLY'):
            context['host_dict'] = self._get_host_dict()

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Some users who have GET privileges do not have POST privileges.
        if not self._is_superuser_or_project_owner():
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            return self.redirect

        users_to_review = self.users_to_review
        formset = formset_factory(
            self.form_class, max_num=len(users_to_review))
        formset = formset(
            request.POST, initial=users_to_review, prefix='userform')

        if not formset.is_valid():
            for error in formset.errors:
                messages.error(request, error)
            return self.redirect

        decision = request.POST.get('decision', None)
        if decision == 'approve':
            status_name = 'Active'
            message_verb = 'Approved'
        elif decision == 'deny':
            status_name = 'Denied'
            message_verb = 'Denied'
        else:
            message = f'Unexpected review decision: {decision}.'
            messages.error(request, message)
            return self.redirect

        project_user_status_choice = ProjectUserStatusChoice.objects.get(
            name=status_name)

        num_reviews = 0
        failed_usernames = []
        for form in formset:
            user_form_data = form.cleaned_data
            if not user_form_data['selected']:
                continue
            username = user_form_data.get('username')
            user_obj = User.objects.get(username=username)
            project_user_obj = self.project_obj.projectuser_set.get(
                user=user_obj)
            try:
                self._process_project_user_request(
                    project_user_obj, project_user_status_choice)
            except Exception as e:
                logger.exception(e)
                failed_usernames.append(username)
            else:
                num_reviews += 1

        num_failures = len(failed_usernames)
        num_successes = num_reviews - num_failures

        message = (
            f'{message_verb} {num_successes}/{num_reviews} user requests to '
            f'join the project. {settings.PROGRAM_NAME_SHORT} staff have been '
            f'notified to set up cluster access for each approved request.')
        if num_failures > 0:
            messages.warning(request, message)
            failed_usernames_str = ', '.join(failed_usernames)
            message = f'Failed to process requests by: {failed_usernames_str}.'
            messages.error(request, message)
        else:
            messages.success(request, message)

        return self.redirect

    def _get_host_dict(self):
        """Return a mapping from username to the associated host user,
        which may be None, for each user to review."""
        host_dict = {}
        for user in self.users_to_review:
            username = user.get('username')
            join_requests = ProjectUserJoinRequest.objects.filter(
                project_user__project=self.project_obj,
                project_user__user__username=username,
                host_user__isnull=False)
            if join_requests.exists():
                host_user = join_requests.latest('modified').host_user
            else:
                host_user = None
            host_dict[username] = host_user
        return host_dict

    def _get_users_to_review(self):
        """Return a list of dictionaries representing Users who have
        made requests to join the Project."""
        users_to_review = []
        queryset = self.project_obj.projectuser_set.filter(
            status__name='Pending - Add').order_by('user__username')
        for ele in queryset:
            try:
                reason = ele.projectuserjoinrequest_set.latest(
                    'created').reason
            except ProjectUserJoinRequest.DoesNotExist:
                reason = ProjectUserJoinRequest.DEFAULT_REASON

            user = {
                'username': ele.user.username,
                'first_name': ele.user.first_name,
                'last_name': ele.user.last_name,
                'email': ele.user.email,
                'role': ele.role,
                'reason': reason
            }
            users_to_review.append(user)
        return users_to_review

    def _is_superuser_or_project_owner(self):
        """Return whether the requesting user is a superuser or an
        'Active' Project PI or manager."""
        user = self.request.user
        if user.is_superuser:
            return True
        if self.project_obj.projectuser_set.filter(
                user=user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True
        return False

    @staticmethod
    def _process_project_user_request(project_user_obj,
                                      project_user_status_choice):
        """Given a ProjectUser, set its status to the given one, and run
        any additional processing."""
        with transaction.atomic():
            project_user_obj.status = project_user_status_choice
            project_user_obj.save()
            if project_user_status_choice.name == 'Active':
                runner_factory = NewProjectUserRunnerFactory()
                runner = runner_factory.get_runner(
                    project_user_obj, NewProjectUserSource.JOINED)
                runner.run()
            else:
                try:
                    send_project_join_request_denial_email(
                        project_user_obj.project, project_user_obj)
                except Exception as e:
                    message = (
                        f'Failed to send notification email. Details:\n{e}')
                    logger.exception(message)


class ProjectJoinRequestListView(LoginRequiredMixin, UserPassesTestMixin,
                                 ListView):
    template_name = 'project/project_join_request_list.html'
    paginate_by = 25

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + 'created'
        else:
            order_by = '-created'

        project_join_requests = \
            ProjectUserJoinRequest.objects.filter(
                pk__in=ProjectUserJoinRequest.objects.filter(
                    project_user__status__name=
                    'Pending - Add').order_by(
                    'project_user', '-created').distinct(
                    'project_user'))

        join_request_search_form = JoinRequestSearchForm(self.request.GET)

        if join_request_search_form.is_valid():
            data = join_request_search_form.cleaned_data

            if data.get('username'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__user__username__icontains=data.get(
                            'username'))

            if data.get('email'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__user__email__icontains=data.get('email'))

            if data.get('project_name'):
                project_join_requests = \
                    project_join_requests.filter(
                        project_user__project__name__icontains=data.get(
                            'project_name'))

        return project_join_requests.order_by(order_by)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_projectuserjoinrequest'):
            return True

        message = (
            'You do not have permission to view project join requests.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        join_request_search_form = JoinRequestSearchForm(self.request.GET)
        if join_request_search_form.is_valid():
            context['join_request_search_form'] = join_request_search_form
            data = join_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['join_request_search_form'] = join_request_search_form
        else:
            filter_parameters = None
            context['join_request_search_form'] = JoinRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = (
                filter_parameters +
                'order_by=%s&direction=%s&' % (order_by, direction))
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = \
            filter_parameters_with_order_by

        join_request_queryset = self.get_queryset()

        paginator = Paginator(join_request_queryset, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            join_requests = paginator.page(page)
        except PageNotAnInteger:
            join_requests = paginator.page(1)
        except EmptyPage:
            join_requests = paginator.page(paginator.num_pages)

        context['join_request_list'] = join_requests

        return context
