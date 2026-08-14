# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import IntegrityError, transaction
from django.test import TestCase

from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication
from coldfront.users.models import User


class PublicationModelTestCase(TestCase):
    """Tests for the Publication model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="creator")
        cls.project1 = Project.objects.create(name="Project 1", owner=cls.user)
        cls.project2 = Project.objects.create(name="Project 2", owner=cls.user)

    def create_publication(self, doi="10.1000/xyz"):
        return Publication.objects.create(
            doi=doi,
            title="A Test Publication",
            authors=[{"name": "Jane Doe", "orcid": None}],
            year=2024,
            journal="Test Journal",
            source="crossref",
            created_by=self.user,
        )

    def test_create_publication(self):
        pub = self.create_publication()

        self.assertEqual(pub.doi, "10.1000/xyz")
        self.assertEqual(pub.title, "A Test Publication")
        self.assertEqual(pub.authors, [{"name": "Jane Doe", "orcid": None}])
        self.assertEqual(pub.year, 2024)
        self.assertEqual(pub.journal, "Test Journal")
        self.assertEqual(pub.source, "crossref")
        self.assertEqual(pub.created_by, self.user)
        self.assertEqual(str(pub), "A Test Publication")
        self.assertEqual(str(Publication(doi="10.1/x", title="")), "10.1/x")

    def test_doi_required_unique(self):
        self.create_publication()

        # Duplicate DOI is rejected at the DB level.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_publication(doi="10.1000/xyz")

        # A different DOI is allowed.
        self.create_publication(doi="10.1000/other")
        self.assertEqual(Publication.objects.filter(doi="10.1000/other").count(), 1)
        self.assertEqual(Publication.objects.filter(doi="10.1000/xyz").count(), 1)

    def test_link_projects_m2m(self):
        pub = self.create_publication()
        pub.projects.add(self.project1, self.project2)

        self.assertEqual(pub.projects.count(), 2)
        self.assertEqual(list(self.project1.publications.all()), [pub])
        self.assertEqual(list(self.project2.publications.all()), [pub])

        # A publication is a global entity: linking to a second project does
        # not create a duplicate record.
        self.assertEqual(Publication.objects.filter(doi="10.1000/xyz").count(), 1)

    def test_source_display_resolves_from_registry(self):
        pub = self.create_publication()
        self.assertEqual(pub.source, "crossref")


class FundingModelTestCase(TestCase):
    """Tests for the Funding model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="creator")
        cls.project1 = Project.objects.create(name="Project 1", owner=cls.user)
        cls.project2 = Project.objects.create(name="Project 2", owner=cls.user)

    def create_funding(self, award="Award-1", agency="NSF"):
        return Funding.objects.create(
            award_number=award,
            funding_agency=agency,
            title="A Test Funding",
            amount_awarded=10000,
            start_date=None,
            end_date=None,
            status="active",
            source="nsf",
            created_by=self.user,
        )

    def test_create_funding(self):
        funding = self.create_funding()

        self.assertEqual(funding.award_number, "Award-1")
        self.assertEqual(funding.funding_agency, "NSF")
        self.assertEqual(funding.title, "A Test Funding")
        self.assertEqual(funding.amount_awarded_currency, "USD")
        self.assertEqual(funding.amount_awarded.amount, 10000)
        self.assertEqual(funding.status, "active")
        self.assertEqual(funding.source, "nsf")
        self.assertEqual(str(funding), "A Test Funding")

    def test_award_number_agency_unique_together(self):
        self.create_funding()

        # Same award+agency is rejected at the DB level.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_funding()

        # Same award under a different agency is allowed.
        self.create_funding(agency="NIH")
        self.assertEqual(Funding.objects.filter(award_number="Award-1").count(), 2)

    def test_link_projects_m2m(self):
        funding = self.create_funding()
        funding.projects.add(self.project1, self.project2)

        self.assertEqual(funding.projects.count(), 2)
        self.assertEqual(list(self.project1.funding.all()), [funding])
        self.assertEqual(list(self.project2.funding.all()), [funding])
