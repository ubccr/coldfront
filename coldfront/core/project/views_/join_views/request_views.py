import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import TemplateView

from flags.state import flag_enabled

from coldfront.core.project.forms import ProjectSearchForm
from coldfront.core.project.forms import ProjectSelectHostUserForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils import annotate_queryset_with_cluster_name
from coldfront.core.project.utils import send_project_join_notification_email
from coldfront.core.project.views import ProjectListView
from coldfront.core.user.utils import needs_host


logger = logging.getLogger(__name__)


class ProjectJoinView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        user_obj = self.request.user
        project_users = project_obj.projectuser_set.filter(user=user_obj)
        reason = self.request.POST.get('reason')

        if self.request.user.userprofile.access_agreement_signed_date is None:
            messages.error(
                self.request, 'You must sign the User Access Agreement before you can join a project.')
            return False

        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        if project_obj.status == inactive_project_status:
            message = (
                f'Project {project_obj.name} is inactive, and may not be '
                f'joined.')
            messages.error(self.request, message)
            return False

        if project_users.exists():
            project_user = project_users.first()
            if project_user.status.name == 'Active':
                message = (
                    f'You are already a member of Project {project_obj.name}.')
                messages.error(self.request, message)
                return False
            if project_user.status.name == 'Pending - Add':
                message = (
                    f'You have already requested to join Project '
                    f'{project_obj.name}.')
                messages.warning(self.request, message)
                return False

            pending_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Pending')
            processing_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')

            if ProjectUserRemovalRequest.objects. \
                    filter(project_user=project_user,
                           status__in=[pending_status, processing_status]).exists():
                message = (
                    f'You cannot join Project {project_obj.name} because you '
                    f'have a pending removal request for '
                    f'{project_obj.name}.')
                messages.error(self.request, message)
                return False

        # If the user is the requester or PI on a pending request for the
        # Project, do not allow the join request.
        if project_obj.name.startswith('vector_'):
            request_model = VectorProjectAllocationRequest
        else:
            request_model = SavioProjectAllocationRequest
        is_requester_or_pi = Q(requester=user_obj) | Q(pi=user_obj)
        if request_model.objects.filter(
                is_requester_or_pi, project=project_obj,
                status__name__in=['Under Review', 'Approved - Processing']):
            message = (
                f'You are the requester or PI of a pending request for '
                f'Project {project_obj.name}, so you may not join it. You '
                f'will automatically be added when it is approved.')
            messages.warning(self.request, message)
            return False

        if len(reason) < 20:
            message = 'Please provide a valid reason to join the project (min 20 characters)'
            messages.error(self.request, message)
            return False

        return True

    def get(self, *args, **kwargs):
        return redirect(self.login_url)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        user_obj = self.request.user
        project_users = project_obj.projectuser_set.filter(user=user_obj)
        role = ProjectUserRoleChoice.objects.get(name='User')
        status = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        reason = self.request.POST['reason']

        select_host_user_form = ProjectSelectHostUserForm(
            project=project_obj.name,
            data=self.request.POST)
        host_user = None
        if select_host_user_form.is_valid():
            host_user = \
                User.objects.get(
                    username=select_host_user_form.cleaned_data['host_user'])

        if project_users.exists():
            project_user = project_users.first()
            project_user.role = role
            # If the user is Active on the project, raise a warning and exit.
            if project_user.status.name == 'Active':
                message = (
                    f'You are already an Active member of Project '
                    f'{project_obj.name}.')
                messages.warning(self.request, message)
                next_view = reverse('project-join-list')
                return redirect(next_view)
            project_user.status = status
            project_user.save()
        else:
            project_user = ProjectUser.objects.create(
                user=user_obj,
                project=project_obj,
                role=role,
                status=status)

        # Create a join request
        ProjectUserJoinRequest.objects.create(project_user=project_user,
                                              reason=reason,
                                              host_user=host_user)

        message = (
            f'You have requested to join Project {project_obj.name}. The '
            f'managers have been notified.')
        messages.success(self.request, message)
        next_view = reverse('project-join-list')

        # Send a notification to the project managers.
        try:
            send_project_join_notification_email(project_obj, project_user)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.logger.error(message)
            self.logger.exception(e)

        return redirect(next_view)


class ProjectJoinListView(ProjectListView, UserPassesTestMixin):

    template_name = 'project/project_join_list.html'

    def test_func(self):
        user = self.request.user
        if user.userprofile.access_agreement_signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can join '
                'a project.')
            messages.error(self.request, message)
            return False
        return True

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

        projects = Project.objects.prefetch_related(
            'field_of_science', 'status').filter(
                status__name__in=['New', 'Active', ]
        ).order_by(order_by)
        projects = annotate_queryset_with_cluster_name(projects)

        if project_search_form.is_valid():
            data = project_search_form.cleaned_data

            # Last Name
            if data.get('last_name'):
                pi_project_users = ProjectUser.objects.filter(
                    project__in=projects,
                    role__name='Principal Investigator',
                    user__last_name__icontains=data.get('last_name'))
                project_ids = pi_project_users.values_list(
                    'project_id', flat=True)
                projects = projects.filter(id__in=project_ids)

            # Username
            if data.get('username'):
                projects = projects.filter(
                    Q(projectuser__user__username__icontains=data.get(
                        'username')) &
                    (Q(projectuser__role__name='Principal Investigator') |
                     Q(projectuser__status__name='Active'))
                )

            # Field of Science
            if data.get('field_of_science'):
                projects = projects.filter(
                    field_of_science__description__icontains=data.get(
                        'field_of_science'))

            # Project Title
            if data.get('project_title'):
                projects = projects.filter(title__icontains=data.get('project_title'))

            # Project Name
            if data.get('project_name'):
                projects = projects.filter(name__icontains=data.get('project_name'))

            # Cluster Name
            if data.get('cluster_name'):
                projects = projects.filter(cluster_name__icontains=data.get('cluster_name'))

        return projects.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = self.get_queryset()
        user_obj = self.request.user

        # A User may not join a Project he/she is already a pending or active
        # member of.
        already_pending_or_active = set(projects.filter(
            projectuser__user=user_obj,
            projectuser__status__name__in=['Pending - Add', 'Active', ]
        ).values_list('name', flat=True))
        # A User may not join a Project with a pending
        # SavioProjectAllocationRequest where he/she is the requester or PI.
        is_requester_or_pi = Q(requester=user_obj) | Q(pi=user_obj)
        pending_project_request_statuses = [
            'Under Review', 'Approved - Processing']
        is_part_of_pending_savio_project_request = set(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'project'
            ).filter(
                is_requester_or_pi,
                status__name__in=pending_project_request_statuses
            ).values_list('project__name', flat=True))
        # A User may not join a Project with a pending
        # VectorProjectAllocationRequest where he/she is the requester or PI.
        is_part_of_pending_vector_project_request = set(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'project'
            ).filter(
                is_requester_or_pi,
                status__name__in=pending_project_request_statuses
            ).values_list('project__name', flat=True))
        pending_removal_requests = set([removal_request.project_user.project.name
                                        for removal_request in
                                        ProjectUserRemovalRequest.objects.filter(
                                            Q(project_user__user__username=self.request.user.username) &
                                            Q(status__name='Pending'))])

        not_joinable = set.union(
            already_pending_or_active,
            is_part_of_pending_savio_project_request,
            is_part_of_pending_vector_project_request,
            pending_removal_requests)

        join_requests = Project.objects.filter(Q(projectuser__user=self.request.user)
                                               & Q(status__name__in=['New', 'Active', ])
                                               & Q(projectuser__status__name__in=['Pending - Add']))
        join_requests = annotate_queryset_with_cluster_name(join_requests)

        context['join_requests'] = join_requests
        context['not_joinable'] = not_joinable

        # Only non-LBL employees without a host user and without any pending
        # join requests need access to the SelectHostUserForm.
        context['need_host'] = False
        pending_status = ProjectUserStatusChoice.objects.get(name='Pending - Add')
        if flag_enabled('LRC_ONLY') \
                and needs_host(self.request.user) \
                and not ProjectUser.objects.filter(user=self.request.user,
                                                   status=pending_status).exists():
            context['need_host'] = True

            selecthostform_dict = {}
            for project in context.get('project_list'):
                selecthostform_dict[project.name] = \
                    ProjectSelectHostUserForm(project=project.name)

            context['selecthostform_dict'] = selecthostform_dict

        return context
