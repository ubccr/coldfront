import logging
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from coldfront.core.project.models import Project
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template
from coldfront.plugins.pi_search.forms import PISearchForm


EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')

logger = logging.getLogger(__name__)


@login_required
def pi_search_view(request):
    context = {'form': PISearchForm()}
    return render(request, "pi_search/pi_search.html", context)


class PISearchResultsView(LoginRequiredMixin, ListView):
    template_name = 'pi_search/pi_search_results.html'

    def post(self, request, *args, **kwargs):
        pi_username = request.POST.get('pi_username')
        context = {}
        context["pi_username"] = pi_username
        projects = Project.objects.prefetch_related('pi', 'status',).filter(
            pi__username=pi_username,
            projectuser__status__name='Active',
            status__name__in=['New', 'Active', 'Review Pending'],
            private=False
        ).distinct()

        context["pi_project_users"] = {}
        for project in projects:
            context["pi_project_users"][project.pk] = project.projectuser_set.filter(
                status__name='Active').values_list('user', flat=True)

        context["pi_projects"] = projects
        context['EMAIL_ENABLED'] = EMAIL_ENABLED
        return render(request, self.template_name, context)


class RequestAccessEmailView(LoginRequiredMixin, View):

    def post(self, request):
        project_obj = get_object_or_404(Project, pk=request.POST.get('project_pk'))
        if project_obj.private is True:
            logger.warning(
                "User {} attempted to request access to a private project (pk={})".format(
                    request.user.username, project_obj.pk
                )
            )
            return HttpResponseForbidden(reverse('project-list'))

        domain_url = get_domain_url(self.request)
        project_url = '{}{}'.format(domain_url, reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if EMAIL_ENABLED:
            send_email_template(
                'Add User to Project Request',
                'pi_search/email/project_add_user_request.txt',
                {
                    'center_name': EMAIL_CENTER_NAME,
                    'user': request.user,
                    'project_title': project_obj.title,
                    'project_url': project_url,
                    'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                    'signature': EMAIL_SIGNATURE
                },
                EMAIL_TICKET_SYSTEM_ADDRESS,
                [project_obj.pi.email]
            )
            logger.info(
                f'User {request.user.username} sent an email to {project_obj.pi.email} requesting '
                f'access to their project (project pk={project_obj.pk})'
            )
        else:
            logger.warning('Email has not been enabled')
            return HttpResponseForbidden(reverse('project-list'))

        return HttpResponseRedirect(reverse('project-list'))