# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import ast
import io
import re
import uuid

import requests
from bibtexparser.bibdatabase import as_text
from bibtexparser.bparser import BibTexParser
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView
from doi2bib import crossref

from coldfront.core.project.models import Project
from coldfront.core.publication.forms import (
    PublicationAddForm,
    PublicationDeleteForm,
    PublicationExportForm,
    PublicationResultForm,
    PublicationSearchForm,
)
from coldfront.core.publication.models import Publication, PublicationSource

MANUAL_SOURCE = "manual"


class PublicationSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "publication/publication_add_publication_search.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add publications to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["publication_search_form"] = PublicationSearchForm()
        context["project"] = Project.objects.get(pk=self.kwargs.get("project_pk"))
        return context


class PublicationSearchResultView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "publication/publication_add_publication_search_result.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add publications to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"project_pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def _search_id(self, unique_id):
        matching_source_obj = None
        for source in PublicationSource.objects.all():
            if source.name == "doi":
                try:
                    status, bib_str = crossref.get_bib(unique_id)
                    bp = BibTexParser(interpolate_strings=False)
                    bib_database = bp.parse(bib_str)
                    bib_json = bib_database.entries[0]
                    matching_source_obj = source
                    break
                except Exception:
                    continue

            elif source.name == "adsabs":
                try:
                    url = "http://adsabs.harvard.edu/cgi-bin/nph-bib_query?bibcode={}&data_type=BIBTEX".format(
                        unique_id
                    )
                    r = requests.get(url, timeout=5)
                    bp = BibTexParser(interpolate_strings=False)
                    bib_database = bp.parse(r.text)
                    bib_json = bib_database.entries[0]
                    matching_source_obj = source
                    break
                except Exception:
                    continue

        if not matching_source_obj:
            return False

        year = as_text(bib_json["year"])
        author = (
            as_text(bib_json["author"])
            .replace("{\\textquotesingle}", "'")
            .replace("{\\textendash}", "-")
            .replace("{\\textemdash}", "-")
            .replace("{\\textasciigrave}", " ")
            .replace("{\\textdaggerdbl}", " ")
            .replace("{\\textdagger}", " ")
        )
        title = (
            as_text(bib_json["title"])
            .replace("{\\textquotesingle}", "'")
            .replace("{\\textendash}", "-")
            .replace("{\\textemdash}", "-")
            .replace("{\\textasciigrave}", " ")
            .replace("{\\textdaggerdbl}", " ")
            .replace("{\\textdagger}", " ")
        )

        author = re.sub("{|}", "", author)
        title = re.sub("{|}", "", title)

        # not all bibtex entries will have a journal field
        if "journal" in bib_json:
            journal = (
                as_text(bib_json["journal"])
                .replace("{\\textquotesingle}", "'")
                .replace("{\\textendash}", "-")
                .replace("{\\textemdash}", "-")
                .replace("{\\textasciigrave}", " ")
                .replace("{\\textdaggerdbl}", " ")
                .replace("{\\textdagger}", " ")
            )
            journal = re.sub("{|}", "", journal)
        else:
            # fallback: clearly indicate that data was absent
            source_name = matching_source_obj.name
            journal = "[no journal info from {}]".format(source_name.upper())

        pub_dict = {}
        pub_dict["author"] = author
        pub_dict["year"] = year
        pub_dict["title"] = title
        pub_dict["journal"] = journal
        pub_dict["unique_id"] = unique_id
        pub_dict["source_pk"] = matching_source_obj.pk

        return pub_dict

    def post(self, request, *args, **kwargs):
        search_ids = list(set(request.POST.get("search_id").split()))
        project_pk = self.kwargs.get("project_pk")

        project_obj = get_object_or_404(Project, pk=project_pk)
        pubs = []
        for ele in search_ids:
            pub_dict = self._search_id(ele)
            if pub_dict:
                pubs.append(pub_dict)

        formset = formset_factory(PublicationResultForm, max_num=len(pubs))
        formset = formset(initial=pubs, prefix="pubform")

        context = {}
        context["project_pk"] = project_obj.pk
        context["formset"] = formset
        context["search_ids"] = search_ids
        context["pubs"] = pubs

        return render(request, self.template_name, context)


class PublicationAddView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add publications to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        pubs = ast.literal_eval(request.POST.get("pubs"))
        project_pk = self.kwargs.get("project_pk")

        project_obj = get_object_or_404(Project, pk=project_pk)
        formset = formset_factory(PublicationResultForm, max_num=len(pubs))
        formset = formset(request.POST, initial=pubs, prefix="pubform")

        publications_added = 0
        publications_skipped = []
        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data

                if form_data["selected"]:
                    source_obj = PublicationSource.objects.get(pk=form_data.get("source_pk"))
                    author = form_data.get("author")
                    if len(author) > 1024:
                        author = author[:1024]
                    publication_obj, created = Publication.objects.get_or_create(
                        project=project_obj,
                        unique_id=form_data.get("unique_id"),
                        defaults={
                            "title": form_data.get("title"),
                            "author": author,
                            "year": form_data.get("year"),
                            "journal": form_data.get("journal"),
                            "source": source_obj,
                        },
                    )
                    if created:
                        publications_added += 1
                    else:
                        publications_skipped.append(form_data.get("unique_id"))

            msg = ""
            if publications_added:
                msg += "Added {} publication{} to project.".format(
                    publications_added, "s" if publications_added > 1 else ""
                )
            if publications_skipped:
                msg += "Publication already exists on this project. Skipped adding: {}".format(
                    ", ".join(publications_skipped)
                )

            messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_pk}))


class PublicationAddManuallyView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = PublicationAddForm
    template_name = "publication/publication_add_publication_manually.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permission to add a new publication to this project.")

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot add publications to an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["source"] = MANUAL_SOURCE
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        Publication.objects.create(
            project=project_obj,
            title=form_data.get("title"),
            author=form_data.get("author"),
            year=form_data.get("year"),
            journal=form_data.get("journal"),
            unique_id=uuid.uuid4(),
            source=PublicationSource.objects.get(name=MANUAL_SOURCE),
        )

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["project"] = Project.objects.get(pk=self.kwargs.get("project_pk"))
        return context

    def get_success_url(self):
        messages.success(self.request, "Added a publication.")
        return reverse("project-detail", kwargs={"pk": self.kwargs.get("project_pk")})


class PublicationDeletePublicationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "publication/publication_delete_publications.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permission to delete publications from this project.")

    def get_publications_to_delete(self, project_obj):
        publications_do_delete = [
            {"title": publication.title, "year": publication.year}
            for publication in project_obj.publication_set.all().order_by("-year")
        ]

        return publications_do_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        publications_do_delete = self.get_publications_to_delete(project_obj)
        context = {}

        if publications_do_delete:
            formset = formset_factory(PublicationDeleteForm, max_num=len(publications_do_delete))
            formset = formset(initial=publications_do_delete, prefix="publicationform")
            context["formset"] = formset

        context["project"] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        publications_do_delete = self.get_publications_to_delete(project_obj)

        formset = formset_factory(PublicationDeleteForm, max_num=len(publications_do_delete))
        formset = formset(request.POST, initial=publications_do_delete, prefix="publicationform")

        publications_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                publication_form_data = form.cleaned_data
                if publication_form_data["selected"]:
                    publication_obj = Publication.objects.get(
                        project=project_obj,
                        title=publication_form_data.get("title"),
                        year=publication_form_data.get("year"),
                    )
                    publication_obj.delete()
                    publications_deleted_count += 1

            messages.success(request, "Deleted {} publications from project.".format(publications_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project.id})


class PublicationExportPublicationsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "publication/publication_export_publications.html"

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True

        messages.error(self.request, "You do not have permission to delete publications from this project.")

    def get_publications_to_export(self, project_obj):
        publications_do_delete = [
            {
                "title": publication.title,
                "year": publication.year,
                "unique_id": publication.unique_id,
            }
            for publication in project_obj.publication_set.all().order_by("-year")
        ]

        return publications_do_delete

    def get(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        publications_do_export = self.get_publications_to_export(project_obj)
        context = {}

        if publications_do_export:
            formset = formset_factory(PublicationExportForm, max_num=len(publications_do_export))
            formset = formset(initial=publications_do_export, prefix="publicationform")
            context["formset"] = formset

        context["project"] = project_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        publications_do_export = self.get_publications_to_export(project_obj)

        formset = formset_factory(PublicationExportForm, max_num=len(publications_do_export))
        formset = formset(request.POST, initial=publications_do_export, prefix="publicationform")

        bib_text = ""
        if formset.is_valid():
            for form in formset:
                publication_form_data = form.cleaned_data
                if publication_form_data["selected"]:
                    publication_obj = Publication.objects.get(
                        project=project_obj,
                        title=publication_form_data.get("title"),
                        year=publication_form_data.get("year"),
                        unique_id=publication_form_data.get("unique_id"),
                    )
                    print("id is" + publication_obj.display_uid())
                    publication_obj.display_uid()
                    status, bib_str = crossref.get_bib(publication_obj.display_uid())
                    bp = BibTexParser(interpolate_strings=False)
                    bp.parse(bib_str)
                    bib_text += bib_str
            response = HttpResponse(content_type="text/plain")
            response["Content-Disposition"] = "attachment; filename=refs.bib"
            buffer = io.StringIO()
            buffer.write(bib_text)
            output = buffer.getvalue()
            buffer.close()
            response.write(output)
            return response
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.object.project.id})
