# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from urllib.parse import quote

import requests
from django.conf import settings

from coldfront.ris.models import Funding
from coldfront.ris.providers.base import ResearchWorkProviderClient
from coldfront.ris.registry import register_research_work_provider

from . import NSFConfig


class NSFError(Exception):
    """Raised when the NSF Awards API call fails."""


def get_config():
    """
    Return the NSF provider configuration from PLUGINS_CONFIG.
    """
    return settings.PLUGINS_CONFIG.get(NSFConfig.name, {})


@register_research_work_provider(Funding)
class NSFClient(ResearchWorkProviderClient):
    """
    A thin, self-contained client for the public NSF Awards API
    (https://api.nsf.gov/services/v1/awards.json). NSF is an API-only provider:
    no OAuth link or login is required. It returns ``Funding`` instances
    (unsaved) for import/search.
    """

    @classmethod
    def display_name(cls):
        return "NSF"

    base_url = "https://api.nsf.gov/services/v1"

    def __init__(self, config=None):
        self.config = config if config is not None else get_config()

    def _get(self, url):
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            raise NSFError(f"NSF request failed (HTTP {response.status_code}).")
        return response.json()

    def search_fundings(self, query, rpp=50, offset=0):
        """
        Search NSF awards by free-text ``query`` and return unsaved ``Funding``
        instances. Awards missing an id or agency are dropped (both are required
        on every Funding).
        """
        url = f"{self.base_url}/awards.json?keyword={quote(query)}&rpp={rpp}&offset={offset}"
        awards = self._get(url).get("response", {}).get("award", [])

        fundings = []
        for award in awards:
            award_number = award.get("id")
            agency = award.get("agency")
            if not award_number or not agency:
                continue
            fundings.append(
                Funding(
                    award_number=str(award_number),
                    funding_agency=agency,
                    title=award.get("title") or "(untitled award)",
                    amount_awarded=_amount(award.get("estimatedTotalAmt")),
                    start_date=_date(award.get("startDate")),
                    end_date=_date(award.get("expDate")),
                    status="active" if award.get("activeAwd") else "expired",
                    source="nsf",
                    external_id=str(award_number),
                )
            )
        return fundings

    key = "nsf"

    def search(self, model, user, limit, filterset=None):
        """
        Search awards using the fields a bound django-filter ``filterset``
        supports. NSF's Awards API is keyword based, so the supported fields
        (``q``, ``title``, ``award_number``, ``funding_agency``, ``status``)
        are read from ``filterset.form.cleaned_data`` and combined into a
        single keyword. Returns unsaved ``Funding`` instances, or an empty
        list when no searchable field is set or when no ``filterset`` was
        supplied (API-only provider). At most ``limit`` records are requested.
        """
        if filterset is None:
            return []
        filter_data = filterset.form.cleaned_data
        parts = []
        for key in ("q", "title", "award_number", "funding_agency", "status"):
            value = filter_data.get(key)
            if value:
                parts.append(str(value))
        if not parts:
            return []
        return self.search_fundings(" ".join(parts), rpp=limit)

    def fetch(self, model, user, external_ids):
        """Re-fetch awards by id (the NSF external_id)."""
        return self.fetch_funding(external_ids)

    def fetch_funding(self, award_ids):
        """
        Fetch one or more awards by id and return a list of unsaved ``Funding``
        instances (used for refresh/detail), one per input award id. Failed
        lookups map to ``None``.

        The NSF Awards API has no multi-award endpoint, so each award is
        fetched with its own request. The API wraps even a single award in a
        ``response.award`` list, so the first element is taken.
        """
        if isinstance(award_ids, (str, int)):
            award_ids = [award_ids]

        fundings = []
        for award_id in award_ids:
            try:
                awards = (
                    self._get(f"{self.base_url}/awards/{quote(str(award_id), safe='')}.json")
                    .get("response", {})
                    .get("award", [])
                )
                award = awards[0] if awards else {}
                fundings.append(
                    Funding(
                        award_number=str(award.get("id") or ""),
                        funding_agency=award.get("agency") or "",
                        title=award.get("title") or "(untitled award)",
                        amount_awarded=_amount(award.get("estimatedTotalAmt")),
                        start_date=_date(award.get("startDate")),
                        end_date=_date(award.get("expDate")),
                        status="active" if award.get("activeAwd") else "expired",
                        source="nsf",
                        external_id=str(award.get("id") or ""),
                    )
                )
            except Exception:
                fundings.append(None)
        return fundings


def _amount(value):
    """Convert an award amount string to a Decimal."""
    if not value:
        return None
    try:
        from decimal import Decimal

        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (TypeError, ValueError, ArithmeticError):
        return None


def _date(value):
    """Convert an mm/dd/yyyy date string to a Python date."""
    if not value:
        return None
    try:
        # NSF Awards API uses the US mm/dd/yyyy format.
        from datetime import datetime

        return datetime.strptime(value, "%m/%d/%Y").date()
    except (TypeError, ValueError):
        return None
