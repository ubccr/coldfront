# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.ris.providers.base import ResearchWorkProviderClient


class LocalProvider(ResearchWorkProviderClient):
    """
    Search provider over the local database for a specific project.

    ``search`` filters at the database level: the project's not-yet-linked
    records of ``model`` are filtered through the bound django-filter
    ``filterset`` (``filter_queryset``), so only matching rows are ever pulled
    out of the database, and at most ``limit`` are returned. ``fetch`` is never
    used: local records are linked directly by their primary key.
    """

    key = "local"

    @classmethod
    def display_name(cls):
        return "Local"

    def __init__(self, project):
        self.project = project

    def search(self, model, user, limit, filterset=None):
        # Local records are only searched when a filter is applied, matching the
        # API-only providers.
        if filterset is None:
            return []
        qs = model.objects.exclude(projects=self.project)
        # django-filter's ``filter_queryset`` reads ``form.cleaned_data``,
        # which is only populated after validation. Trigger validation here
        # (idempotent; the add/link view already validates once) so the
        # provider works standalone too.
        filterset.errors
        qs = filterset.filter_queryset(qs)
        return list(qs[:limit])

    def fetch(self, model, user, external_ids):
        return [None] * len(external_ids)
