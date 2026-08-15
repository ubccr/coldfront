# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Base contract for research-work providers (Publications/Funding) in the ris app.

Providers subclass ``ResearchWorkProviderClient`` and are registered via
``register_research_work_provider`` so that the add/link views can drive them
uniformly.

``search`` receives a bound django-filter ``FilterSet`` built from the add/link
view's query params (validated once by the view). API-only providers (Crossref,
NSF) and the local provider require a ``filterset`` and return no candidates
when it is ``None``; providers that read a user's linked account (e.g. ORCID)
return the user's records unfiltered when ``filterset`` is ``None``. If a
provider filters candidates locally (e.g. ORCID), that is its own
implementation detail and lives in the provider, not here.
"""

from django.utils.translation import gettext as _

__all__ = ("ResearchWorkProviderClient",)


class ResearchWorkProviderClient:
    """
    Abstract contract for providers that search/fetch research works
    (publications/funding).

    Concrete providers subclass this, set ``key`` (the stable provider
    identifier persisted on records as ``source``/``provider``), and implement
    ``display_name()``, ``search`` and ``fetch``.

    ``search(model, user, limit, filterset)`` returns at most ``limit`` matching
    candidates for ``model`` given a bound django-filter ``FilterSet`` (the
    add/link view builds and validates it once, so
    ``filterset.form.cleaned_data`` is populated and ``filterset.filter_queryset``
    is safe for queryset-based providers; a ``None`` filterset means no
    searchable filter was applied). ``fetch`` re-fetches the records whose
    provider ``external_id`` values are listed in ``external_ids``, returning
    one instance per id (failed lookups map to ``None``). Both may raise; the
    views catch and skip providers.
    """

    key = ""

    @classmethod
    def display_name(cls):
        """Return a human-readable display name for this provider."""
        raise NotImplementedError(_("{class_name} must implement display_name()").format(class_name=cls.__name__))

    def search(self, model, user, limit, filterset=None):
        """Return at most ``limit`` matching candidates for ``model``."""
        raise NotImplementedError(_("{class_name} must implement search()").format(class_name=self.__class__.__name__))

    def fetch(self, model, user, external_ids):
        """Re-fetch records by provider external_id; failed lookups map to None."""
        raise NotImplementedError(_("{class_name} must implement fetch()").format(class_name=self.__class__.__name__))
