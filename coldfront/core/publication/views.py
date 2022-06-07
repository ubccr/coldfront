import hashlib
import imp
import json
from pipes import Template
import re

from typing import Any, Dict, List, Tuple, Union
from django.conf import settings

import requests
import os
import io
from io import StringIO
from bibtexparser.bibdatabase import as_text
from bibtexparser.bparser import BibTexParser
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.forms import formset_factory
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DetailView, ListView, TemplateView, View
from django.views.generic.edit import FormView
from django.views.static import serve

from coldfront.core.user.models import User, UserProfile
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.publication.forms import (
    PublicationAddForm,
    PublicationDeleteForm,
    PublicationResultForm,
    PublicationSearchForm,
    PublicationExportForm,
    PublicationUserSelectForm,
)
from coldfront.core.publication.models import Publication, PublicationSource
from doi2bib import crossref
from coldfront.core.user.forms import UserSelectForm
from coldfront.core.user.views import UserSelectResults
# import orcid #NEW REQUIREMENT: orcid (pip install orcid)
from coldfront.orcid_vars import OrcidAPI

from coldfront.dict_methods import get_value_or_default

MANUAL_SOURCE = 'manual'


class PublicationSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_add_publication_search.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        if UserSelectResults.SELECTED_KEY in self.request.session:
            selected_ids = self.request.session.pop(UserSelectResults.SELECTED_KEY)
            selected_user_profiles = UserProfile.objects.filter(user_id__in=selected_ids)
            selected_orcids = list(selected_user_profiles.values_list('orcid_id', flat=True))
            
            psf_initial = {
                'search_id': '\n'.join(filter(lambda elem: elem is not None, selected_orcids)),
            }
            context['publication_search_form'] = PublicationSearchForm(initial=psf_initial)
            context['search_immediately'] = True
        else:
            context['publication_search_form'] = PublicationSearchForm()
            context['search_immediately'] = False
        
        context['project'] = Project.objects.get(
            pk=self.kwargs.get('project_pk'))
        return context


class PublicationSearchResultView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_add_publication_search_result.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'project_pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)


    def _search_id(self, unique_id) -> Union[dict, bool]:
        def _gen_pub_dic_doi(matching_source_obj, bib_json, unique_id) -> Union[dict, bool]:
            """Get a publication dictionary for doi

            Returns
            -------
            :returns: dict, False
                The dictionary on success, otherwise false.
            """
            if not matching_source_obj:
                return False

            year = as_text(bib_json['year'])
            author = as_text(bib_json['author']).replace('{\\textquotesingle}', "'").replace('{\\textendash}', '-').replace(
                '{\\textemdash}', '-').replace('{\\textasciigrave}', ' ').replace('{\\textdaggerdbl}', ' ').replace('{\\textdagger}', ' ')
            title = as_text(bib_json['title']).replace('{\\textquotesingle}', "'").replace('{\\textendash}', '-').replace(
                '{\\textemdash}', '-').replace('{\\textasciigrave}', ' ').replace('{\\textdaggerdbl}', ' ').replace('{\\textdagger}', ' ')

            author = re.sub("{|}", "", author)
            title = re.sub("{|}", "", title)

            # not all bibtex entries will have a journal field
            if 'journal' in bib_json:
                journal = as_text(bib_json['journal']).replace('{\\textquotesingle}', "'").replace('{\\textendash}', '-').replace(
                    '{\\textemdash}', '-').replace('{\\textasciigrave}', ' ').replace('{\\textdaggerdbl}', ' ').replace('{\\textdagger}', ' ')
                journal = re.sub("{|}", "", journal)
            else:
                # fallback: clearly indicate that data was absent
                source_name = matching_source_obj.name
                journal = '[no journal info from {}]'.format(source_name.upper())

            pub_dict_entree = {}
            pub_dict_entree['author'] = author
            pub_dict_entree['year'] = year
            pub_dict_entree['title'] = title
            pub_dict_entree['journal'] = journal
            pub_dict_entree['unique_id'] = unique_id
            pub_dict_entree['source_pk'] = matching_source_obj.pk

            # Uncomment to generate pub_dict_entree dump
            # log_file = open("pub_dict_dump.json", "w")
            # log_file.write(json.dumps(pub_dict_entree, indent=2))
            # log_file.close()

            return [pub_dict_entree]
        
        def _gen_pub_dic_orc(matching_source_obj, orc_record, unique_id, orc_id, orc_token) -> Union[dict, bool]:
            """Get a publication dictionary for ORCID

            Returns
            -------
            :returns: dict, False
                The dictionary on success, otherwise false.
            """
            # # Uncomment for orc record dump
            # log_file = open("orc_record_dump.json", "w")
            # log_file.write(json.dumps(orc_record, indent=2))
            # log_file.close()

            orc_works = orc_record['group']
            orc_worksummary = [works['work-summary'][0] for works in orc_works]

            orc_pub_dict = []

            for work in orc_worksummary:
                orc_pub_dict_entree = {}

                orc_pub_dict_entree['title'] = get_value_or_default(work, "title", "title", "value",
                    default_value="[No Title]")
                orc_pub_dict_entree['author'] = get_value_or_default(work, "source", "source-name", "value",
                    default_value="[No Author]")
                # Program wants only 4 characters for year, but year is optional in ORCID
                # Program crashes w/out int for year, so I'll put in a future year
                # to signify a missing date
                orc_pub_dict_entree['year'] = get_value_or_default(work, "publication-date", "year", "value",
                    default_value=9999)
                orc_pub_dict_entree['unique_id'] = get_value_or_default(work, "path",
                    default_value="[No ID]").strip("/")
                orc_pub_dict_entree['source_pk'] = matching_source_obj.pk

                try:
                    # Not all the required info is in the summary.
                    # Get more detailed info from put-code
                    putcode = work['put-code']
                    orc_work_full = OrcidAPI.orc_api.read_record_public(orc_id, f'works/{putcode}', orc_token)
                    orc_work_full = orc_work_full['bulk'][0]['work']

                    orc_pub_dict_entree['journal'] = get_value_or_default(orc_work_full, 'journal-title', 'value',
                        default_value="[No Journal]")
                except:
                    pass
                
                orc_pub_dict.append(orc_pub_dict_entree)
            
            return orc_pub_dict
        
        matching_source_obj = None

        for source in PublicationSource.objects.all():
            if (source.name == 'doi' or source.name == 'adsabs'):
                if source.name == 'doi':
                    try:
                        status, bib_str = crossref.get_bib(unique_id)
                        bp = BibTexParser(interpolate_strings=False)
                        bib_database = bp.parse(bib_str)
                        bib_json = bib_database.entries[0]
                        matching_source_obj = source
                        
                        return _gen_pub_dic_doi(matching_source_obj, bib_json, unique_id)
                    except:
                        continue

                elif source.name == 'adsabs':
                    try:
                        url = 'http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode={}&data_type=BIBTEX'.format(
                            unique_id)
                        r = requests.get(url, timeout=5)
                        bp = BibTexParser(interpolate_strings=False)
                        bib_database = bp.parse(r.text)
                        bib_json = bib_database.entries[0]
                        matching_source_obj = source
                        
                        return _gen_pub_dic_doi(matching_source_obj, bib_json, unique_id)
                    except:
                        continue
            
            elif source.name == 'orcid':
                # Code for Orcid here

                try:
                    # Regex the ORCID id from input
                    orc_id_match = re.search(OrcidAPI.ORC_RE_KEY, unique_id)

                    if (orc_id_match):
                        orc_id : str = orc_id_match.group()

                        orc_token = OrcidAPI.orc_api.get_search_token_from_orcid()

                        # url is for a sign-in page
                        # url = orcid_vars.orc_api.get_login_url('/authenticate', ORC_REDIRECT)

                        # Can only find researchers in sandbox env if app is in sandbox
                        orc_record : dict = OrcidAPI.orc_api.read_record_public(orc_id, 'works', orc_token)       

                        matching_source_obj = source
                        return _gen_pub_dic_orc(matching_source_obj, orc_record, unique_id, orc_id, orc_token)
                except Exception:
                    continue

        return False

    def post(self, request, *args, **kwargs):
        search_ids = list(set(request.POST.get('search_id').split()))
        project_pk = self.kwargs.get('project_pk')

        project_obj = get_object_or_404(Project, pk=project_pk)
        pubs = []
        for ele in search_ids:
            pub_dict = self._search_id(ele)
            if pub_dict:
                for pub_dict_entree in pub_dict:
                    if pub_dict_entree:
                        pubs.append(pub_dict_entree)

        formset = formset_factory(PublicationResultForm, max_num=len(pubs))
        formset = formset(initial=pubs, prefix='pubform')

        has_orcid = re.search(OrcidAPI.ORC_RE_KEY, ele) is not None
        # True if the system detects an ORCID, but the ORCID API is not set up
        missing_orcid_api = has_orcid and not OrcidAPI.orcid_configured()

        context = {}
        context['project_pk'] = project_obj.pk
        context['formset'] = formset
        context['search_ids'] = search_ids
        context['pubs'] = pubs
        context['missing_orcid_api'] = missing_orcid_api

        return render(request, self.template_name, context)


class PublicationAddView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)        

    def post(self, request, *args, **kwargs):
        pubs = eval(request.POST.get('pubs'))
        project_pk = self.kwargs.get('project_pk')

        project_obj = get_object_or_404(Project, pk=project_pk)
        formset = formset_factory(PublicationResultForm, max_num=len(pubs))
        formset = formset(request.POST, initial=pubs, prefix='pubform')

        publications_added = 0
        publications_skipped = []
        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                created = False

                # Was missing if statement to check if element was selected
                if form_data['selected']:
                    source_obj = PublicationSource.objects.get(
                        pk=form_data.get('source_pk'))
                    author = form_data.get('author')
                    if len(author) > 1024: author = author[:1024]
                    publication_obj, created = Publication.objects.get_or_create(
                        project=project_obj,
                        unique_id=form_data.get('unique_id'),
                        defaults = {
                            'title':form_data.get('title'),
                            'author':author,
                            'year':form_data.get('year'),
                            'journal':form_data.get('journal'),
                            'source':source_obj                            
                        }                        
                    )
                    if created:
                        publications_added += 1
                    else:
                        publications_skipped.append(form_data.get('unique_id'))

            msg = ''
            if publications_added:
                msg += 'Added {} publication{} to project.'.format(
                    publications_added, 's' if publications_added > 1 else '')
                if publications_skipped:
                    # Add space to separate the messages generated from
                    # publications_added and publications_skipped
                    msg += ' '
            if publications_skipped:
                msg += 'Publication already exists on this project. Skipped adding: {}'.format(
                    ', '.join(publications_skipped))

            messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_pk}))


class PublicationAddManuallyView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = PublicationAddForm
    template_name = 'publication/publication_add_publication_manually.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to add a new publication to this project.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot add publications to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['source'] = MANUAL_SOURCE
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        pub_obj = Publication.objects.create(
            project=project_obj,
            title=form_data.get('title'),
            author=form_data.get('author'),
            year=form_data.get('year'),
            journal=form_data.get('journal'),
            unique_id=uuid.uuid4(),
            source=PublicationSource.objects.get(name=MANUAL_SOURCE),
        )

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['project'] = Project.objects.get(pk=self.kwargs.get('project_pk'))
        return context

    def get_success_url(self):
        messages.success(self.request, 'Added a publication.')
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})


class PublicationUserOrcidImportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True
    
    def get(self, request, *args, **kwargs):
        project_pk = kwargs['project_pk']

        # User selection
        proj_users = ProjectUser.objects.filter(project_id=project_pk)
        proj_user_ids = proj_users.values_list("user_id", flat=True)
        user_ids = list(User.objects.filter(pk__in=proj_user_ids).values_list('pk', flat=True))

        redirect_key = reverse('publication-search', kwargs={'project_pk': project_pk})

        ## Code to enable user search. ##
        # request.session[UserSelectResults.AVAIL_KEY] = user_ids
        # request.session[UserSelectResults.REDIRECT_KEY] = redirect_key
        # # user-select-home is in Users
        # return HttpResponseRedirect(reverse('user-select-home'))

        ## Code to just use all project users. ##
        request.session[UserSelectResults.SELECTED_KEY] = user_ids
        return HttpResponseRedirect(redirect_key)


class PublicationDeletePublicationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_delete_publications.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to delete publications from this project.')

    def get_publications_to_delete(self, project_obj):

        publications_do_delete = [
            {'title': publication.title,
             'year': publication.year}
            for publication in project_obj.publication_set.all().order_by('-year')
        ]

        return publications_do_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        publications_do_delete = self.get_publications_to_delete(project_obj)
        context = {}

        if publications_do_delete:
            formset = formset_factory(
                PublicationDeleteForm, max_num=len(publications_do_delete))
            formset = formset(initial=publications_do_delete,
                              prefix='publicationform')
            context['formset'] = formset

        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        publications_do_delete = self.get_publications_to_delete(project_obj)
        context = {}

        formset = formset_factory(
            PublicationDeleteForm, max_num=len(publications_do_delete))
        formset = formset(
            request.POST, initial=publications_do_delete, prefix='publicationform')

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

            messages.success(request, 'Deleted {} publications from project.'.format(
                publications_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})


class PublicationExportPublicationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'publication/publication_export_publications.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to delete publications from this project.')

    def get_publications_to_export(self, project_obj):

        publications_do_delete = [
            {'title': publication.title,
             'year': publication.year,
             'unique_id': publication.unique_id, }
            for publication in project_obj.publication_set.all().order_by('-year')
        ]

        return publications_do_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        publications_do_export = self.get_publications_to_export(project_obj)
        context = {}

        if publications_do_export:
            formset = formset_factory(
                PublicationExportForm, max_num=len(publications_do_export))
            formset = formset(initial=publications_do_export,
                              prefix='publicationform')
            context['formset'] = formset

        context['project'] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        publications_do_export = self.get_publications_to_export(project_obj)
        context = {}

        formset = formset_factory(
            PublicationExportForm, max_num=len(publications_do_export))
        formset = formset(
            request.POST, initial=publications_do_export, prefix='publicationform')

        publications_deleted_count = 0
        bib_text = ''
        if formset.is_valid():
            for form in formset:
                publication_form_data = form.cleaned_data
                if publication_form_data['selected']:

                    publication_obj = Publication.objects.get(
                        project=project_obj,
                        title=publication_form_data.get('title'),
                        year=publication_form_data.get('year'),
                        unique_id=publication_form_data.get('unique_id'),
                    )
                    print("id is"+publication_obj.display_uid())
                    temp_id = publication_obj.display_uid()

                    orc_id = re.match(OrcidAPI.ORC_RE_KEY, temp_id)
                    if (orc_id):  # Evaluate for ORCID instead of DOI
                        putcode = re.search("[0-9]{7}", temp_id)

                        orc_token : str = OrcidAPI.orc_api.get_search_token_from_orcid()
                        orc_record : dict = OrcidAPI.orc_api.read_record_public(orc_id.group(0), 'work', orc_token, putcode.group(0))   

                        bib_str = json.dumps(orc_record, indent=2)
                    else:
                        status, bib_str = crossref.get_bib(publication_obj.display_uid())
                        bp = BibTexParser(interpolate_strings=False)
                        bib_database = bp.parse(bib_str)
                    bib_text += bib_str + "\n"
            response = HttpResponse(content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename=refs.bib'
            buffer = io.StringIO()
            buffer.write(bib_text)
            output = buffer.getvalue()
            buffer.close()
            response.write(output)
            return response
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.object.project.id})
