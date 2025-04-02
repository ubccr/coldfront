import logging

from django.shortcuts import render
from django.forms import formset_factory
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404

from coldfront.plugins.academic_analytics.forms import PublicationForm
from coldfront.plugins.academic_analytics.utils import (get_publications,
                                                        remove_existing_publications,
                                                        add_publication)
from coldfront.core.project.models import Project

logger = logging.getLogger(__name__)


class AcademicAnalyticsPublications(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'academic_analytics/publications.html'

    def test_func(self):
        project_pk = self.request.GET.get('project_pk')
        if not project_pk:
            project_pk = self.request.POST.get('project_pk')
        project_obj = get_object_or_404(Project, pk=project_pk)
        if self.request.user.is_superuser:
            return True

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=request.GET.get('project_pk'))

        context = {}
        context['project_pk'] = request.GET.get('project_pk')
        context['publication_formset'] = []
        usernames = project_obj.projectuser_set.filter(status__name='Active').values_list('user__username', flat=True)
        publication_data = get_publications(usernames)
        publication_data = remove_existing_publications(project_obj, publication_data)
        if publication_data:
            publication_formset = formset_factory(PublicationForm, max_num=len(publication_data))
            publication_formset = publication_formset(initial=publication_data, prefix='publicationform')
            context['publication_formset'] = publication_formset

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=request.POST.get('project_pk'))

        context = {}
        context['project_pk'] = request.POST.get('project_pk')
        context['publication_formset'] = []
        usernames = project_obj.projectuser_set.filter(status__name='Active').values_list('user__username', flat=True)
        publication_data = get_publications(usernames)
        publication_data = remove_existing_publications(project_obj, publication_data)
        num_added_pubs = 0
        if publication_data:
            publication_formset = formset_factory(PublicationForm, max_num=len(publication_data))
            publication_formset = publication_formset(request.POST, initial=publication_data, prefix='publicationform')
            if publication_formset.is_valid():
                for form in publication_formset:
                    data = form.cleaned_data
                    if data.get("add"):
                        add_publication(project_obj, data)
                        num_added_pubs += 1
            else:
                raise Exception('Error adding publications')

        if num_added_pubs:
            logger.info(f'{num_added_pubs} aa publications were added to a project with id {project_obj.pk}')

        publication_data = remove_existing_publications(project_obj, publication_data)
        if publication_data:
            publication_formset = formset_factory(PublicationForm, max_num=len(publication_data))
            publication_formset = publication_formset(initial=publication_data, prefix='publicationform')
            context['publication_formset'] = publication_formset

        return render(request, self.template_name, context)
