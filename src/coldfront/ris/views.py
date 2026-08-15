# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component

from coldfront.ras.models import Project
from coldfront.ras.views.projects import ProjectBulkUnlinkView
from coldfront.registry import register_model_view
from coldfront.ris import filtersets, forms, tables
from coldfront.ris.models import Funding, Publication
from coldfront.ris.providers.local import LocalProvider
from coldfront.users.permissions import get_permission_for_model
from coldfront.views import ViewTab, generic
from coldfront.views.generic.base import BaseObjectView
from coldfront.views.htmx import htmx_partial
from coldfront.views.object_actions import BulkExport

from .object_actions import UnlinkFunding, UnlinkPublications
from .registry import get_providers_for_model

__all__ = (
    "FundingBulkDeleteView",
    "FundingBulkEditView",
    "FundingBulkImportView",
    "FundingDeleteView",
    "FundingEditView",
    "FundingListView",
    "FundingView",
    "ProjectAddFundingView",
    "ProjectAddPublicationView",
    "ProjectAddResearchWorkView",
    "ProjectFundingBulkUnlinkView",
    "ProjectFundingTabView",
    "ProjectPublicationBulkUnlinkView",
    "ProjectPublicationTabView",
    "PublicationBulkDeleteView",
    "PublicationBulkEditView",
    "PublicationBulkImportView",
    "PublicationDeleteView",
    "PublicationEditView",
    "PublicationListView",
    "PublicationView",
)


#
# Publications
#


@register_model_view(Publication, "list", path="", detail=False)
class PublicationListView(generic.ObjectListView):
    queryset = Publication.objects.all()
    filterset = filtersets.PublicationFilterSet
    filterset_form = forms.PublicationFilterSetForm
    table = tables.PublicationTable


@register_model_view(Publication)
class PublicationView(generic.ObjectView):
    queryset = Publication.objects.all()


@register_model_view(Publication, "add", detail=False)
@register_model_view(Publication, "edit")
class PublicationEditView(generic.ObjectEditView):
    queryset = Publication.objects.all()
    form = forms.PublicationForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.source = "manual"
            obj.created_by = request.user
        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(Publication, "delete")
class PublicationDeleteView(generic.ObjectDeleteView):
    queryset = Publication.objects.all()


@register_model_view(Publication, "bulk_import", path="import", detail=False)
class PublicationBulkImportView(generic.BulkImportView):
    queryset = Publication.objects.all()
    model_form = forms.PublicationImportForm


@register_model_view(Publication, "bulk_edit", path="edit", detail=False)
class PublicationBulkEditView(generic.BulkEditView):
    queryset = Publication.objects.all()
    filterset = filtersets.PublicationFilterSet
    table = tables.PublicationTable
    form = forms.PublicationBulkEditForm


@register_model_view(Publication, "bulk_delete", path="delete", detail=False)
class PublicationBulkDeleteView(generic.BulkDeleteView):
    queryset = Publication.objects.all()
    filterset = filtersets.PublicationFilterSet
    table = tables.PublicationTable


#
# Funding
#


@register_model_view(Funding, "list", path="", detail=False)
class FundingListView(generic.ObjectListView):
    queryset = Funding.objects.all()
    filterset = filtersets.FundingFilterSet
    filterset_form = forms.FundingFilterSetForm
    table = tables.FundingTable


@register_model_view(Funding)
class FundingView(generic.ObjectView):
    queryset = Funding.objects.all()


@register_model_view(Funding, "add", detail=False)
@register_model_view(Funding, "edit")
class FundingEditView(generic.ObjectEditView):
    queryset = Funding.objects.all()
    form = forms.FundingForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.source = "manual"
            obj.created_by = request.user
        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(Funding, "delete")
class FundingDeleteView(generic.ObjectDeleteView):
    queryset = Funding.objects.all()


@register_model_view(Funding, "bulk_import", path="import", detail=False)
class FundingBulkImportView(generic.BulkImportView):
    queryset = Funding.objects.all()
    model_form = forms.FundingImportForm


@register_model_view(Funding, "bulk_edit", path="edit", detail=False)
class FundingBulkEditView(generic.BulkEditView):
    queryset = Funding.objects.all()
    filterset = filtersets.FundingFilterSet
    table = tables.FundingTable
    form = forms.FundingBulkEditForm


@register_model_view(Funding, "bulk_delete", path="delete", detail=False)
class FundingBulkDeleteView(generic.BulkDeleteView):
    queryset = Funding.objects.all()
    filterset = filtersets.FundingFilterSet
    table = tables.FundingTable


#
# Project tabs: publications & funding linked to a project
#


@register_model_view(Project, "publications", path="publications")
class ProjectPublicationTabView(generic.ObjectChildrenView):
    actions = (BulkExport, UnlinkPublications)
    queryset = Project.objects.all()
    child_model = Publication
    table = tables.PublicationTable
    filterset = filtersets.PublicationFilterSet
    filterset_form = forms.PublicationFilterSetForm
    template_name = "ras/project/publications.html"
    tab = ViewTab(
        label=_("Publications"),
        badge=lambda obj: obj.publications.count(),
        permission="ras.view_publication",
        weight=300,
    )

    def get_children(self, request, parent):
        return Publication.objects.restrict(request.user, "view").filter(projects=parent)


@register_model_view(Project, "funding", path="funding")
class ProjectFundingTabView(generic.ObjectChildrenView):
    actions = (BulkExport, UnlinkFunding)
    queryset = Project.objects.all()
    child_model = Funding
    table = tables.FundingTable
    filterset = filtersets.FundingFilterSet
    filterset_form = forms.FundingFilterSetForm
    template_name = "ras/project/funding.html"
    tab = ViewTab(
        label=_("Funding"),
        badge=lambda obj: obj.funding.count(),
        permission="ras.view_funding",
        weight=700,
    )

    def get_children(self, request, parent):
        return Funding.objects.restrict(request.user, "view").filter(projects=parent)


#
# Project bulk-unlink views: remove child records' links to the current project.
#
# The generic base view lives in ``coldfront.ras.views.projects``; the concrete
# subclasses here wire in the ris-specific queryset/filterset/table for each model.
#


@register_model_view(Project, "publication_bulk_unlink", path="publications/bulk-unlink", detail=True)
class ProjectPublicationBulkUnlinkView(ProjectBulkUnlinkView):
    queryset = Publication.objects.all()
    filterset = filtersets.PublicationFilterSet
    table = tables.PublicationTable
    return_url_name = "ras:project_publications"
    child_relation = "publications"


@register_model_view(Project, "funding_bulk_unlink", path="funding/bulk-unlink", detail=True)
class ProjectFundingBulkUnlinkView(ProjectBulkUnlinkView):
    queryset = Funding.objects.all()
    filterset = filtersets.FundingFilterSet
    table = tables.FundingTable
    return_url_name = "ras:project_funding"
    child_relation = "funding"


#
# Project link views: add publications/funding from local records + providers
#


def _get_or_create_publication(fetched, source, external_id):
    """
    Persist a re-fetched publication, updating its fields in place if it
    already exists. Returns (obj, created).
    """
    obj, created = Publication.objects.get_or_create(
        doi=fetched.doi,
        defaults={
            "title": fetched.title,
            "authors": fetched.authors,
            "year": fetched.year,
            "journal": fetched.journal,
            "source": source,
            "external_id": external_id,
        },
    )
    if not created:
        obj.title = fetched.title
        obj.authors = fetched.authors
        obj.year = fetched.year
        obj.journal = fetched.journal
        obj.source = source
        obj.external_id = external_id
        obj.save()
    return obj, created


def _get_or_create_funding(fetched, source, external_id):
    """
    Persist a re-fetched funding record, updating its fields in place if it
    already exists. Returns (obj, created).
    """
    obj, created = Funding.objects.get_or_create(
        award_number=fetched.award_number,
        funding_agency=fetched.funding_agency,
        defaults={
            "title": fetched.title,
            "amount_awarded": fetched.amount_awarded,
            "start_date": fetched.start_date,
            "end_date": fetched.end_date,
            "status": fetched.status,
            "source": source,
            "external_id": external_id,
        },
    )
    if not created:
        obj.title = fetched.title
        obj.amount_awarded = fetched.amount_awarded
        obj.start_date = fetched.start_date
        obj.end_date = fetched.end_date
        obj.status = fetched.status
        obj.source = source
        obj.external_id = external_id
        obj.save()
    return obj, created


class ProjectAddResearchWorkView(BaseObjectView):
    """
    Link research works (publications/funding) to a project from local records
    not yet linked, and from the providers registered for the model (see
    ``coldfront.ris.registry``).

    Providers implement the ``ResearchWorkProviderClient`` contract:
    ``search(model, user, limit, filterset)`` returns at most ``limit``
    matching candidates given a bound django-filter ``FilterSet``, and
    ``fetch(model, user, external_ids)`` re-fetches selected records by their
    provider ``external_id``. Local records are served by ``LocalProvider``
    (never registered), which filters the project-not-yet-linked records at the
    database level without any view restriction. The provider-search filterset
    is built and validated once here from the query params, separately from the
    rendered filter form.

    Each provider decides whether to search when no filter is applied: API-only
    and local sources return no candidates, while providers that read a user's
    linked account (e.g. ORCID) return the user's records, so the default view
    shows the user's linked records.
    """

    queryset = Project.objects.all()
    permission_action = "change"
    model = None
    key_fields = ()
    filter_form_class = None
    filterset_class = None
    return_url_name = ""
    table_class = None
    model_label = "records"

    def get_required_permission(self):
        return get_permission_for_model(Project, self.permission_action)

    def get(self, request, **kwargs):
        project = self.get_object(**kwargs)
        filter_form = self._filter_form(request)
        filterset = self._search_filterset(request)
        rows = self._build_rows(request, project, filterset)

        table = self.table_class(rows, project=project)
        table.configure(request)

        # HTMX requests (quick search, filter, pagination, ordering) return only
        # the table partial; the target element is swapped, not the whole page.
        if htmx_partial(request):
            return HttpResponse(render_component(request, "table.htmx", table=table, model=self.model))

        return_url = request.GET.get("return_url", reverse(self.return_url_name, kwargs={"pk": project.pk}))

        return render(
            request,
            self.template_name,
            {
                "object": project,
                "project": project,
                "table": table,
                "model": self.model,
                "filter_form": filter_form,
                "return_url": return_url,
                "providers": [cls.display_name() for cls in get_providers_for_model(self.model)],
            },
        )

    def _filter_form(self, request):
        return self.filter_form_class(request.GET)

    def _search_filterset(self, request):
        """
        Build and validate the provider-search ``FilterSet`` for this model.

        The add/link UI keeps its own filter form (``filter_form_class``); the
        provider search instead drives each provider through a bound django-
        filter ``FilterSet`` built from the same query params. Validation
        happens here once: an invalid filterset means no searchable filter was
        applied, so ``None`` is returned (providers then see no filters).
        """
        filterset = self.filterset_class(request.GET)
        if filterset.is_valid():
            return filterset
        return None

    def _candidate_key(self, candidate):
        """Canonical dedup key for a candidate, built from ``key_fields``."""
        values = []
        for field in self.key_fields:
            value = getattr(candidate, field)
            if not value:
                return None
            values.append(str(value).lower())
        return tuple(values)

    def _build_rows(self, request, project, filterset):
        """
        Merge local + provider candidates, dedup by canonical key (local wins).

        Each provider receives the validated ``filterset`` (or ``None`` when no
        searchable filter was applied) and decides itself whether to search:
        API-only providers (Crossref, NSF) and the local provider return no
        candidates without a filter, while providers that read a user's linked
        account (e.g. ORCID) return the user's records unfiltered. Each
        provider returns at most ``limit`` candidates.
        """
        rows = []
        seen = set()
        limit = settings.DEFAULT_RESEARCH_WORK_PROVIDER_SEARCH_LIMIT

        clients = [LocalProvider(project=project)]
        clients.extend(cls() for cls in get_providers_for_model(self.model))

        for client in clients:
            try:
                for candidate in client.search(self.model, request.user, limit, filterset):
                    key = self._candidate_key(candidate)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    if isinstance(client, LocalProvider):
                        rows.append(self._local_row(candidate))
                    else:
                        rows.append(self._external_row(candidate))
            except Exception:
                continue
        return rows

    def post(self, request, **kwargs):
        project = self.get_object(**kwargs)
        selected = request.POST.getlist("pk")
        return_url = request.POST.get("return_url", reverse(self.return_url_name, kwargs={"pk": project.pk}))

        created = 0
        linked = 0

        # Local records: link directly, no provider call needed.
        for value in selected:
            if not value.startswith("local:"):
                continue
            pk = int(value[len("local:") :])
            obj = self.model.objects.filter(pk=pk).first()
            if obj is None or project in obj.projects.all():
                continue
            obj.projects.add(project)
            linked += 1

        # External records: group by provider so each provider is queried once.
        external = {}
        for value in selected:
            if not value.startswith("external:"):
                continue
            parts = value[len("external:") :].split("|")
            external.setdefault(parts[0], []).append((value, parts[0], parts[1], parts[2:]))

        fetched_by_key = self._refetch_all(request, external)

        for value in selected:
            if not value.startswith("external:"):
                continue
            parts = value[len("external:") :].split("|")
            source, external_id = parts[0], parts[1]
            key_fields = dict(zip(self.key_fields, parts[2:]))
            fetched = fetched_by_key.get(value)
            if fetched is None:
                obj, _ = self.model.objects.get_or_create(
                    **key_fields, defaults={"source": source, "external_id": external_id}
                )
            else:
                obj, _ = self._persist_fetched(fetched, source, external_id)
            if project not in obj.projects.all():
                obj.projects.add(project)
                created += 1
            else:
                linked += 1

        messages.success(request, f"{created} {self.model_label} created and {linked} linked.")
        return redirect(return_url)

    def _refetch_all(self, request, external):
        """
        Re-fetch external records grouped by provider, issuing a single provider
        call per provider. Returns a mapping of row key -> fetched instance or
        None (when the provider is unregistered, fails, or has no linked
        account).
        """
        providers = {cls.key: cls for cls in get_providers_for_model(self.model)}
        fetched = {}
        for source, rows in external.items():
            keys = [row[0] for row in rows]
            external_ids = [row[2] for row in rows]
            client = providers.get(source)
            if client is None:
                for key in keys:
                    fetched[key] = None
                continue
            try:
                cands = client().fetch(self.model, request.user, external_ids)
                for key, cand in zip(keys, cands):
                    fetched[key] = cand
            except Exception:
                for key in keys:
                    fetched[key] = None
        return fetched


@register_model_view(Project, "add_publication", path="add-publication")
class ProjectAddPublicationView(ProjectAddResearchWorkView):
    """
    Link publications to a project from local records, the user's linked ORCID
    record, and Crossref search results. Requires the ``ras.change_project``
    permission.
    """

    template_name = "ris/publication_add.html"
    model = Publication
    key_fields = ("doi",)
    filter_form_class = forms.PublicationAddFilterForm
    filterset_class = filtersets.PublicationFilterSet
    return_url_name = "ras:project_publications"
    table_class = tables.PublicationAddTable
    model_label = "publication(s)"

    def _local_row(self, obj):
        return {
            "key": f"local:{obj.pk}",
            "is_local": True,
            "title": obj.title,
            "year": obj.year,
            "journal": obj.journal,
            "doi": obj.doi,
            "source": obj.source,
        }

    def _external_row(self, candidate):
        doi = candidate.doi
        return {
            "key": f"external:{candidate.source}|{candidate.external_id}|{doi}",
            "is_local": False,
            "title": candidate.title,
            "year": candidate.year,
            "journal": candidate.journal,
            "doi": doi,
            "source": candidate.source,
        }

    def _persist_fetched(self, fetched, source, external_id):
        return _get_or_create_publication(fetched, source, external_id)


@register_model_view(Project, "add_funding", path="add-funding")
class ProjectAddFundingView(ProjectAddResearchWorkView):
    """
    Link funding to a project from local records, the user's linked ORCID
    record, and NSF Awards search results. Requires the ``ras.change_project``
    permission.
    """

    template_name = "ris/funding_add.html"
    model = Funding
    key_fields = ("award_number", "funding_agency")
    filter_form_class = forms.FundingAddFilterForm
    filterset_class = filtersets.FundingFilterSet
    return_url_name = "ras:project_funding"
    table_class = tables.FundingAddTable
    model_label = "funding record(s)"

    def _local_row(self, obj):
        return {
            "key": f"local:{obj.pk}",
            "is_local": True,
            "title": obj.title,
            "award_number": obj.award_number,
            "funding_agency": obj.funding_agency,
            "status": obj.status,
            "source": obj.source,
        }

    def _external_row(self, candidate):
        award = candidate.award_number
        agency = candidate.funding_agency
        return {
            "key": f"external:{candidate.source}|{candidate.external_id}|{award}|{agency}",
            "is_local": False,
            "title": candidate.title,
            "award_number": award,
            "funding_agency": agency,
            "status": candidate.status,
            "source": candidate.source,
        }

    def _persist_fetched(self, fetched, source, external_id):
        return _get_or_create_funding(fetched, source, external_id)
