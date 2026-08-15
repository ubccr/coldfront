# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from habanero import Crossref

from coldfront.ris.models import Publication
from coldfront.ris.providers.base import ResearchWorkProviderClient
from coldfront.ris.registry import register_research_work_provider

from . import CrossrefConfig

# Fields requested from the Crossref API. ``select`` limits the payload and
# keeps search fast (see habanero's ``Crossref.works`` ``select`` parameter).
SELECT_FIELDS = ["DOI", "title", "author", "published", "container-title"]


class CrossrefError(Exception):
    """Raised when the Crossref API call fails."""


def get_config():
    """
    Return the Crossref provider configuration from PLUGINS_CONFIG.
    """
    return settings.PLUGINS_CONFIG.get(CrossrefConfig.name, {})


@register_research_work_provider(Publication)
class CrossrefClient(ResearchWorkProviderClient):
    """
    A thin client for the public Crossref REST API, wrapping ``habanero``.

    Crossref is an API-only provider: no OAuth link or login is required. It
    returns ``Publication`` instances (unsaved) for import/search and can later
    be used to refresh a publication's metadata by DOI.

    Configuration is read from ``PLUGINS_CONFIG["coldfront.ris.plugins.crossref"]``
    (e.g. ``base_url``, ``mailto``, ``timeout``), with sensible defaults.
    """

    @classmethod
    def display_name(cls):
        return "Crossref"

    def __init__(self, config=None):
        self.config = config if config is not None else get_config()
        self._client = Crossref(
            base_url=self.config.get("base_url", "https://api.crossref.org"),
            mailto=self.config.get("mailto", ""),
            timeout=self.config.get("timeout", 30),
        )

    def _works(self, **kwargs):
        try:
            return self._client.works(**kwargs)
        except Exception as e:
            raise CrossrefError(f"Crossref request failed ({e})") from e

    def search_works(self, query="", rows=50, **query_kwargs):
        """
        Search Crossref for works matching ``query`` and return unsaved
        ``Publication`` instances. Only DOI-bearing records are returned (a
        DOI is required on every Publication). ``query_kwargs`` are the
        structured field queries habanero supports (e.g. ``query_title``,
        ``query_author``, ``query_container_title``).
        """
        result = self._works(query=query, limit=rows, select=SELECT_FIELDS, **query_kwargs)
        items = _message_items(result)

        publications = []
        for item in items:
            doi = item.get("DOI")
            if not doi:
                continue
            title = (item.get("title") or [""])[0] or ""
            journal = (item.get("container-title") or [""])[0] or ""
            publications.append(
                Publication(
                    doi=doi,
                    title=title,
                    year=_year(item.get("published")),
                    journal=journal,
                    authors=_authors(item.get("author")),
                    source="crossref",
                    external_id=doi,
                )
            )
        return publications

    key = "crossref"

    def search(self, model, user, limit, filterset=None):
        """
        Search works using the fields a bound django-filter ``filterset``
        supports. Only the fields Crossref can honor (``q``, ``title``,
        ``author``, ``journal``) are used, read from
        ``filterset.form.cleaned_data``. Returns unsaved ``Publication``
        instances, or an empty list when no searchable field is set or when no
        ``filterset`` was supplied (API-only provider). At most ``limit``
        records are requested.
        """
        if filterset is None:
            return []
        filter_data = filterset.form.cleaned_data
        query = filter_data.get("q") or ""
        query_kwargs = {}
        for key, param in (
            ("title", "query_title"),
            ("author", "query_author"),
            ("journal", "query_container_title"),
        ):
            value = filter_data.get(key) or ""
            if value:
                query_kwargs[param] = value
        if not query and not query_kwargs:
            return []
        return self.search_works(query=query, rows=limit, **query_kwargs)

    def fetch(self, model, user, external_ids):
        """Re-fetch works by DOI (the Crossref external_id)."""
        return self.fetch_work(external_ids)

    def fetch_work(self, dois):
        """
        Fetch one or more works by DOI and return a list of unsaved
        ``Publication`` instances (used for refresh/sync), one per input DOI.
        Failed lookups map to ``None``.

        Multiple DOIs are requested in a single Crossref call (habanero returns
        one response per DOI, ``warn=True`` turns per-DOI failures into ``None``
        entries instead of raising). The single-work endpoint rejects the
        ``select`` parameter, so the full records are fetched.
        """
        if isinstance(dois, str):
            dois = [dois]

        # ``warn=True`` turns per-DOI HTTP failures into ``None`` entries but
        # emits a ``warnings.warn``; suppress it so strict warning configs (e.g.
        # pytest ``-W error``) don't turn it into an exception.
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = self._works(ids=dois, warn=True)
        if isinstance(result, dict):
            result = [result]

        publications = []
        for res in result:
            if not res:
                publications.append(None)
                continue
            items = _message_items(res)
            item = items[0] if items else {}
            publications.append(
                Publication(
                    doi=item.get("DOI") or "",
                    title=(item.get("title") or [""])[0] or "",
                    year=_year(item.get("published")),
                    journal=(item.get("container-title") or [""])[0] or "",
                    authors=_authors(item.get("author")),
                    source="crossref",
                    external_id=item.get("DOI") or "",
                )
            )
        return publications


def _message_items(result):
    """
    Return the list of work dicts from a Crossref response, handling both the
    single-work shape (``message-type: "work"`` where ``message`` IS the work
    dict, used by ``Crossref.works(ids=...)``) and the work-list shape
    (``message-type: "work-list"`` with ``message.items``, used by searches).
    """
    message = result.get("message") or {}
    if result.get("message-type") == "work" or "DOI" in message:
        return [message]
    return message.get("items") or []


def _year(node):
    """Extract the year from a Crossref ``published`` node (date-parts)."""
    if not node:
        return None
    parts = node.get("date-parts") or []
    if not parts:
        return None
    try:
        return int(parts[0][0])
    except (TypeError, ValueError):
        return None


def _authors(node):
    """Extract the author list as a JSON array of {name, orcid} dicts."""
    if not node:
        return []
    authors = []
    for author in node:
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = " ".join(part for part in (given, family) if part)
        orcid = author.get("ORCID") or author.get("orcid") or ""
        authors.append({"name": name, "orcid": orcid or None})
    return [a for a in authors if a["name"]]
