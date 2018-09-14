import re

import requests
from bibtexparser.bibdatabase import as_text
from bibtexparser.bparser import BibTexParser
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import DetailView, ListView, TemplateView, View
from doi2bib import crossref

from core.djangoapps.project.models import Project
from core.djangoapps.publication.forms import (PublicationDeleteForm,
                                               PublicationSearchForm)
from core.djangoapps.publication.models import Publication, PublicationSource


class PublicationSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_add_publication_search.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['publication_search_form'] = PublicationSearchForm()
        context['project'] = Project.objects.get(pk=self.kwargs.get('project_pk'))
        return context


class PublicationSearchResultView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_add_publication_search_result.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'project_pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        unique_id = request.POST.get('unique_id')
        project_pk = self.kwargs.get('project_pk')

        project_obj = get_object_or_404(Project, pk=project_pk)
        matching_source_obj = None
        for source in PublicationSource.objects.all():
            if source.name == 'doi':
                try:
                    status, bib_str = crossref.get_bib(unique_id)
                    bp = BibTexParser(interpolate_strings=False)
                    bib_database = bp.parse(bib_str)
                    bib_json = bib_database.entries[0]
                    matching_source_obj = source
                    break
                except:
                    continue

            elif source.name == 'adsabs':
                try:
                    url = 'http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode={}&data_type=BIBTEX'.format(unique_id)
                    r = requests.get(url, timeout=5)
                    bp = BibTexParser(interpolate_strings=False)
                    bib_database = bp.parse(r.text)
                    bib_json = bib_database.entries[0]
                    matching_source_obj = source
                    break
                except:
                    continue

        if not matching_source_obj:
            return render(request, self.template_name, {})

        year = as_text(bib_json['year'])
        author = as_text(bib_json['author']).replace('{\\textquotesingle}', "'").replace('{\\textendash}', '-').replace('{\\textemdash}', '-').replace('{\\textasciigrave}', ' ').replace('{\\textdaggerdbl}', ' ').replace('{\\textdagger}', ' ')
        title = as_text(bib_json['title']).replace('{\\textquotesingle}', "'").replace('{\\textendash}', '-').replace('{\\textemdash}', '-').replace('{\\textasciigrave}', ' ').replace('{\\textdaggerdbl}', ' ').replace('{\\textdagger}', ' ')

        author = re.sub("{|}", "", author)
        title = re.sub("{|}", "", title)
        context = {}
        context['author'] = author
        context['year'] = year
        context['title'] = title
        context['unique_id'] = unique_id
        context['source'] = matching_source_obj
        context['project_pk'] = project_obj.pk

        return render(request, self.template_name, context)


class PublicationAddView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        title = request.POST.get('title')
        author = request.POST.get('author')
        year = request.POST.get('year')
        source_pk = request.POST.get('source')
        unique_id = request.POST.get('unique_id')
        project_pk = self.kwargs.get('project_pk')

        project_obj = get_object_or_404(Project, pk=project_pk)
        source_obj = get_object_or_404(PublicationSource, pk=source_pk)

        try:
            publication_obj = Publication.objects.create(
                project=project_obj,
                title=title,
                author=author,
                year=year,
                unique_id=unique_id,
                source=source_obj
            )
            messages.success(request, 'Added publication to project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_pk}))
        except IntegrityError as e:
            messages.warning(request, 'Publication "{}" already in project.'.format(title))
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_pk}))


class PublicationDeletePublicationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_delete_publications.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to delete publications from this project.')

    def get_publications_to_delete(self, project_obj):

        publications_do_delete = [
            {'title': publication.title,
             'year': publication.year}
            for publication in project_obj.publication_set.all().order_by('-year')
        ]

        return publications_do_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        publications_do_delete = self.get_publications_to_delete(project_obj)
        context = {}

        if publications_do_delete:
            formset = formset_factory(PublicationDeleteForm, max_num=len(publications_do_delete))
            formset = formset(initial=publications_do_delete, prefix='publicationform')
            context['formset'] = formset

        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        publications_do_delete = self.get_publications_to_delete(project_obj)
        context = {}

        formset = formset_factory(PublicationDeleteForm, max_num=len(publications_do_delete))
        formset = formset(request.POST, initial=publications_do_delete, prefix='publicationform')

        publications_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                publication_form_data = form.cleaned_data
                if publication_form_data['selected']:

                    publication_obj = Publication.objects.get(
                        project=project_obj,
                        title=publication_form_data.get('title'),
                        year=publication_form_data.get('year')
                    )
                    publication_obj.delete()
                    publications_deleted_count += 1

            messages.success(request, 'Deleted {} publications from project.'.format(publications_deleted_count))
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})
