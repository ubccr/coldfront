# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import re
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings

from coldfront.account.models import ThirdPartyAccount
from coldfront.ris.models import Funding, Publication
from coldfront.ris.providers.base import ResearchWorkProviderClient
from coldfront.ris.registry import register_research_work_provider

from . import OrcidConfig

# ORCID iD format: 0000-0000-0000-0000 (16 digits, grouped by fours).
ORCID_ID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{4}$")

# Fields used to build the free-text ``q`` haystack for each research model.
_SEARCH_FIELDS = {
    Publication: ("title", "doi", "journal"),
    Funding: ("title", "award_number", "funding_agency"),
}


class ORCIDError(Exception):
    """Raised when an ORCID API call fails."""


def get_config():
    """
    Return the ORCID provider configuration from PLUGINS_CONFIG.
    """
    return settings.PLUGINS_CONFIG.get(OrcidConfig.name, {})


@register_research_work_provider(Publication)
@register_research_work_provider(Funding)
class ORCIDClient(ResearchWorkProviderClient):
    """
    A thin, self-contained ORCID client. This is the only ORCID-specific code
    in the codebase and borrows nothing from python-social-auth.

    Configuration is read from ``PLUGINS_CONFIG["coldfront.ris.plugins.orcid"]``
    (e.g. client_id, client_secret, base_url, scope), with sensible defaults.
    """

    @classmethod
    def display_name(cls):
        return "ORCID"

    key = "orcid"

    def __init__(self, config=None):
        self.config = config if config is not None else get_config()

    def _get(self, key, default):
        return self.config.get(key, default)

    @property
    def base_url(self):
        return self._get("base_url", "https://orcid.org")

    @property
    def client_id(self):
        return self.config["client_id"]

    @property
    def client_secret(self):
        return self.config["client_secret"]

    @property
    def scope(self):
        return self._get("scope", "/authenticate")

    @property
    def pub_base_url(self):
        """
        Return the public read API host derived from ``base_url``. ORCID's
        public API lives on a ``pub.`` subdomain (pub.orcid.org / pub.sandbox.orcid.org).
        """
        host = urlparse(self.base_url).hostname
        return f"https://pub.{host}"

    def authorize_url(self):
        return f"{self.base_url}/oauth/authorize"

    def token_url(self):
        return f"{self.base_url}/oauth/token"

    def userinfo_url(self):
        return f"{self.base_url}/oauth/userinfo"

    def works_url(self, orcid_id):
        return f"{self.pub_base_url}/v3.0/{orcid_id}/works"

    def work_url(self, orcid_id, put_code):
        return f"{self.pub_base_url}/v3.0/{orcid_id}/work/{put_code}"

    def fundings_url(self, orcid_id):
        return f"{self.pub_base_url}/v3.0/{orcid_id}/fundings"

    def funding_url(self, orcid_id, put_code):
        return f"{self.pub_base_url}/v3.0/{orcid_id}/funding/{put_code}"

    def build_authorize_url(self, state, nonce, redirect_uri):
        """
        Build the ORCID authorization URL for the link-only flow.
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": self.scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
        }
        return f"{self.authorize_url()}?{urlencode(params)}"

    def exchange_code(self, code, redirect_uri):
        """
        Exchange the authorization code for an access token.
        """
        response = requests.post(
            self.token_url(),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if response.status_code != 200:
            raise ORCIDError(f"ORCID token exchange failed (HTTP {response.status_code}).")
        return response.json()

    def fetch_identity(self, access_token):
        """
        Fetch the OpenID Connect userinfo for the access token. ``sub`` is the
        ORCID iD.
        """
        response = requests.get(
            self.userinfo_url(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise ORCIDError(f"ORCID identity fetch failed (HTTP {response.status_code}).")
        return response.json()

    def extract_orcid_id(self, identity, token_response=None):
        """
        Extract and validate the ORCID iD from the userinfo response (preferred)
        or the token response's ``orcid_identifier``.
        """
        orcid = identity.get("sub")
        if not orcid and token_response:
            orcid = token_response.get("orcid_identifier", {}).get("path")
        return self.validate_orcid(orcid)

    def validate_orcid(self, orcid):
        """
        Validate the ORCID iD format; raise ValueError on anything else.
        """
        if not orcid or not ORCID_ID_RE.fullmatch(orcid):
            raise ValueError(f"Invalid ORCID iD: {orcid!r}.")
        return orcid

    def account_id(self, user):
        """Return the linked ORCID iD for ``user``, or None."""
        return _linked_account_id(user, self.key)

    def search(self, model, user, limit, filterset=None):
        """
        Enumerate the linked account's works/fundings (no search API) and return
        at most ``limit`` candidates. ORCID filters candidates locally (it has
        no structured search API), so this is the provider's own implementation
        detail; the filter values are read from ``filterset.form.cleaned_data``
        when a ``filterset`` is supplied. When ``filterset`` is ``None`` the
        user's current works/fundings are returned unfiltered.
        """
        filter_data = filterset.form.cleaned_data if filterset is not None else {}
        account_id = self.account_id(user)
        if not account_id:
            return []
        if model is Publication:
            candidates = self.fetch_works(account_id)
        else:
            candidates = self.fetch_fundings(account_id)

        matched = []
        for candidate in candidates:
            if not self._matches(model, candidate, filter_data):
                continue
            matched.append(candidate)
            if len(matched) >= limit:
                break
        return matched

    def _matches(self, model, candidate, filter_data):
        """
        Return True when ``candidate`` satisfies the cleaned filter-form values
        in ``filter_data``. Model-aware: applies the fields each research
        model's add-view filter form supports. This is ORCID's own local
        filter (it enumerates records rather than searching an API).
        """
        q = (filter_data.get("q") or "").strip().lower()
        if q:
            haystack = " ".join(str(getattr(candidate, field) or "") for field in _SEARCH_FIELDS[model]).lower()
            if q not in haystack:
                return False

        if model is Publication:
            doi = (filter_data.get("doi") or "").strip().lower()
            if doi and doi not in (candidate.doi or "").lower():
                return False
            title = (filter_data.get("title") or "").strip().lower()
            if title and title not in (candidate.title or "").lower():
                return False
            author = (filter_data.get("author") or "").strip().lower()
            if author and not _author_matches(candidate, author):
                return False
            year = filter_data.get("year")
            if year is not None and year != candidate.year:
                return False
            journal = (filter_data.get("journal") or "").strip().lower()
            if journal and journal not in (candidate.journal or "").lower():
                return False
            source = (filter_data.get("source") or "").strip().lower()
            if source and source != (candidate.source or "").lower():
                return False
        else:
            title = (filter_data.get("title") or "").strip().lower()
            if title and title not in (candidate.title or "").lower():
                return False
            award = (filter_data.get("award_number") or "").strip().lower()
            if award and award not in (candidate.award_number or "").lower():
                return False
            agency = (filter_data.get("funding_agency") or "").strip().lower()
            if agency and agency not in (candidate.funding_agency or "").lower():
                return False
            status = (filter_data.get("status") or "").strip().lower()
            if status and status != (candidate.status or "").lower():
                return False
        return True

    def fetch(self, model, user, external_ids):
        """Re-fetch works/fundings by put code (the ORCID external_id)."""
        from coldfront.ris.models import Publication

        account_id = self.account_id(user)
        if not account_id:
            return [None] * len(external_ids)
        put_codes = [int(x) for x in external_ids]
        if model is Publication:
            return self.fetch_work(account_id, put_codes)
        return self.fetch_funding(account_id, put_codes)

    #
    # Public read API (no token): works & fundings for import/sync
    #

    def _request(self, url, **kwargs):
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=30, **kwargs)
        if response.status_code != 200:
            raise ORCIDError(f"ORCID read failed (HTTP {response.status_code}).")
        return response.json()

    def fetch_works(self, orcid_id):
        """
        Fetch the works summaries for an ORCID record and return unsaved
        ``Publication`` instances. Works without a DOI are dropped (a DOI is
        required on every Publication).

        The /works endpoint returns ``group`` entries, each holding one or
        more ``work-summary`` records (one per source), so they are flattened
        into one publication per summary.
        """
        from coldfront.ris.models import Publication

        data = self._request(self.works_url(orcid_id))
        publications = []
        for group in data.get("group", []):
            for work in group.get("work-summary", []):
                put_code = work.get("put-code")
                doi = _extract_external_id(work, "doi")
                if not doi:
                    continue
                publications.append(
                    Publication(
                        doi=doi,
                        title=_first_title(work),
                        year=_year(work.get("publication-date")),
                        journal=_first_title(work.get("journal-title")),
                        source="orcid",
                        external_id=str(put_code) if put_code is not None else "",
                    )
                )
        return publications

    def fetch_work(self, orcid_id, put_codes):
        """
        Fetch the full detail for one or more works by put code and return a
        list of unsaved ``Publication`` instances, one per input put code.
        Failed lookups map to ``None``.

        The ORCID public API has no multi-work endpoint, so each work is
        fetched with its own request.
        """
        from coldfront.ris.models import Publication

        if isinstance(put_codes, int):
            put_codes = [put_codes]

        publications = []
        for put_code in put_codes:
            try:
                data = self._request(self.work_url(orcid_id, put_code))
                doi = _extract_external_id(data, "doi")
                publications.append(
                    Publication(
                        doi=doi or "",
                        title=_first_title(data),
                        year=_year(data.get("publication-date")),
                        journal=_first_title(data.get("journal-title")),
                        authors=_authors(data.get("contributors")),
                        source="orcid",
                        external_id=put_code,
                    )
                )
            except Exception:
                publications.append(None)
        return publications

    def fetch_fundings(self, orcid_id):
        """
        Fetch the funding summaries for an ORCID record and return unsaved
        ``Funding`` instances. Fundings without an award number are dropped.

        The /fundings endpoint returns ``group`` entries, each holding one or
        more ``funding-summary`` records (one per source), so they are
        flattened into one funding per summary.
        """
        from coldfront.ris.models import Funding

        data = self._request(self.fundings_url(orcid_id))
        results = []
        for group in data.get("group", []):
            for funding in group.get("funding-summary", []):
                put_code = funding.get("put-code")
                award_number = _extract_external_id(funding, "grant_number")
                agency = _org_name(funding.get("organization"))
                if not award_number or not agency:
                    continue
                results.append(
                    Funding(
                        award_number=award_number,
                        funding_agency=agency,
                        title=_first_title(funding),
                        start_date=_date(funding.get("start-date")),
                        end_date=_date(funding.get("end-date")),
                        status="",
                        source="orcid",
                        external_id=str(put_code) if put_code is not None else "",
                    )
                )
        return results

    def fetch_funding(self, orcid_id, put_codes):
        """
        Fetch the full detail for one or more fundings by put code and return a
        list of unsaved ``Funding`` instances, one per input put code. Failed
        lookups map to ``None``.

        The ORCID public API has no multi-funding endpoint, so each funding is
        fetched with its own request.
        """
        from coldfront.ris.models import Funding

        if isinstance(put_codes, int):
            put_codes = [put_codes]

        fundings = []
        for put_code in put_codes:
            try:
                data = self._request(self.funding_url(orcid_id, put_code))
                award_number = _extract_external_id(data, "grant_number")
                agency = _org_name(data.get("organization"))
                fundings.append(
                    Funding(
                        award_number=award_number or "",
                        funding_agency=agency or "",
                        title=_first_title(data),
                        amount_awarded=_money(data.get("amount")),
                        start_date=_date(data.get("start-date")),
                        end_date=_date(data.get("end-date")),
                        status="",
                        source="orcid",
                        external_id=put_code,
                    )
                )
            except Exception:
                fundings.append(None)
        return fundings


def _first_title(node):
    """Extract the first title value from an ORCID title node."""
    if not node:
        return ""
    # Some title nodes carry the value directly (e.g. journal-title {"value": ...}).
    if node.get("value"):
        return node["value"]
    title = node.get("title") or {}
    value = title.get("value")
    return value or (title.get("title") or {}).get("value") or ""


def _year(node):
    """Extract the year from an ORCID partial-date node."""
    if not node:
        return None
    year = node.get("year") or {}
    value = year.get("value")
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_external_id(node, id_type):
    """Extract an external id value (e.g. ``doi``, ``grant_number``) from an ORCID node."""
    if not node:
        return ""
    # ORCID v3 uses hyphenated keys (external-ids / external-id / -type / -value);
    # accept the underscore variants too for older fixtures/tests.
    external_ids = node.get("external_ids") or node.get("external-ids") or {}
    for external_id in external_ids.get("external_id", []) + external_ids.get("external-id", []):
        value = external_id.get("external_id_value") or external_id.get("external-id-value") or ""
        if (external_id.get("external_id_type") or external_id.get("external-id-type")) != id_type:
            continue
        # Strip any DOI resolver prefix so we store the bare DOI.
        return value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return ""


def _authors(node):
    """Extract the contributor list as a JSON array of {name, orcid} dicts."""
    if not node:
        return []
    authors = []
    for contributor in node.get("contributor", []):
        credit = contributor.get("credit-name") or {}
        # ORCID credit-name carries the full display name directly.
        name = credit.get("value") or ""
        orcid = (contributor.get("contributor-orcid") or {}).get("path") or ""
        authors.append({"name": name, "orcid": orcid or None})
    return [a for a in authors if a["name"]]


def _org_name(node):
    """Extract the organization name from an ORCID organization node."""
    if not node:
        return ""
    name = node.get("name") or {}
    if isinstance(name, str):
        return name
    return name.get("value") or ""


def _date(node):
    """Convert an ORCID partial-date node to a Python date (Jan-01 for year-only)."""
    if not node:
        return None
    year = (node.get("year") or {}).get("value")
    month = (node.get("month") or {}).get("value") or "01"
    day = (node.get("day") or {}).get("value") or "01"
    if not year:
        return None
    try:
        from django.utils.dateparse import parse_date

        return parse_date(f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
    except (TypeError, ValueError):
        return None


def _currency(node):
    """Extract the currency code from an ORCID amount node."""
    if not node:
        return "USD"
    return node.get("currency-code") or "USD"


def _amount(node):
    """Extract the award amount as a Decimal from an ORCID amount node."""
    if not node:
        return None
    value = node.get("value")
    if not value:
        return None
    try:
        from decimal import Decimal

        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return None


def _money(node):
    """
    Build a ``Money`` instance from an ORCID amount node (validated currency).

    ORCID may return a currency code django-money does not support; such codes
    fall back to the default USD so a single unknown code cannot drop the whole
    funding list. Missing amounts map to None.
    """
    amount = _amount(node)
    if amount is None:
        return None
    try:
        from djmoney.money import Money

        return Money(amount, _currency(node))
    except Exception:
        from djmoney.money import Money

        return Money(amount, "USD")


def _linked_account_id(user, provider):
    """Return the linked account_id for ``provider`` if the user has one."""
    try:
        return user.third_party_accounts.get(provider=provider).account_id
    except ThirdPartyAccount.DoesNotExist:
        return None


def _author_matches(obj, author):
    """
    True if any of ``obj.authors`` (a JSON list of {name, orcid} dicts) contains
    ``author`` (case-insensitive).
    """
    author = author.strip().lower()
    if not author:
        return True
    for entry in obj.authors or []:
        if author in (entry.get("name") or "").lower():
            return True
    return False
