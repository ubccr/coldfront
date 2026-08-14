# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase

from coldfront.ris import registry as ris_registry
from coldfront.ris.models import Funding, Publication
from coldfront.ris.providers.base import ResearchWorkProviderClient
from coldfront.ris.registry import get_providers_for_model, register_research_work_provider


class DummyClient(ResearchWorkProviderClient):
    """Minimal client used to satisfy registry validation in tests."""

    key = "dummy"

    @classmethod
    def display_name(cls):
        return "Dummy"


class ProviderRegistryTestCase(TestCase):
    """Tests for the ris research-work provider registry."""

    def setUp(self):
        self._original = dict(ris_registry.PROVIDER_REGISTRY)
        ris_registry.PROVIDER_REGISTRY.clear()

    def tearDown(self):
        ris_registry.PROVIDER_REGISTRY.clear()
        ris_registry.PROVIDER_REGISTRY.update(self._original)

    def test_register_decorator(self):
        @register_research_work_provider(Publication)
        class Orcid(DummyClient):
            key = "orcid"

        self.assertEqual(get_providers_for_model(Publication), [Orcid])

    def test_stacked_decorators(self):
        @register_research_work_provider(Publication)
        @register_research_work_provider(Funding)
        class Orcid(DummyClient):
            key = "orcid"

        self.assertEqual(get_providers_for_model(Publication), [Orcid])
        self.assertEqual(get_providers_for_model(Funding), [Orcid])

    def test_register_iterable(self):
        @register_research_work_provider((Publication, Funding))
        class Orcid(DummyClient):
            key = "orcid"

        self.assertEqual(get_providers_for_model(Publication), [Orcid])
        self.assertEqual(get_providers_for_model(Funding), [Orcid])

    def test_register_returns_class(self):
        @register_research_work_provider(Publication)
        class Orcid(DummyClient):
            key = "orcid"

        self.assertIsInstance(Orcid, type)

    def test_get_providers_for_model_empty(self):
        self.assertEqual(get_providers_for_model(Publication), [])

    def test_get_providers_for_model_unregistered_model(self):
        # No providers registered for a model not in the registry.
        self.assertEqual(get_providers_for_model(Funding), [])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):

            @register_research_work_provider(Publication)
            class Bad(DummyClient):
                key = ""
                pass

    def test_missing_display_name_raises(self):
        with self.assertRaises(ValueError):

            @register_research_work_provider(Publication)
            class Bad(ResearchWorkProviderClient):
                key = "bad"
                pass

    def test_non_contract_class_raises(self):
        with self.assertRaises(ValueError):

            @register_research_work_provider(Publication)
            class Bad:
                key = "bad"
                pass

    def test_inherited_display_name_allowed(self):
        @register_research_work_provider(Publication)
        class Orcid(DummyClient):
            key = "orcid"

        # display_name() is inherited from DummyClient, not the base stub.
        self.assertEqual(get_providers_for_model(Publication), [Orcid])

    def test_preserves_registration_order(self):
        @register_research_work_provider(Publication)
        class First(DummyClient):
            key = "first"

        @register_research_work_provider(Publication)
        class Second(DummyClient):
            key = "second"

        self.assertEqual(get_providers_for_model(Publication), [First, Second])
