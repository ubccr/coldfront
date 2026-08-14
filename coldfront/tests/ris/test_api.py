# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import date
from decimal import Decimal

from djmoney.money import Money

from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication
from coldfront.users.models import User
from coldfront.utils.testing import APIViewTestCases


class PublicationTest(APIViewTestCases.APIViewTestCase):
    model = Publication
    brief_fields = ["display", "doi", "id", "title", "url", "year"]
    bulk_update_data = {
        "journal": "Updated Journal",
    }

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        projects = (
            Project.objects.create(name="Project 1", owner=owner),
            Project.objects.create(name="Project 2", owner=owner),
            Project.objects.create(name="Project 3", owner=owner),
        )

        publications = (
            Publication.objects.create(doi="10.1000/aaa", title="Publication 1", source="crossref"),
            Publication.objects.create(doi="10.1000/bbb", title="Publication 2", source="crossref"),
            Publication.objects.create(doi="10.1000/ccc", title="Publication 3", source="crossref"),
        )
        publications[0].projects.add(projects[0])
        publications[1].projects.add(projects[0], projects[1])
        publications[2].projects.add(projects[0], projects[1], projects[2])

        cls.create_data = [
            {
                "doi": "10.1000/xyz1",
                "title": "A new publication",
                "year": 2024,
                "journal": "Test Journal",
                "source": "crossref",
            },
            {
                "doi": "10.1000/xyz2",
                "title": "Another publication",
                "year": 2025,
                "journal": "Test Journal",
                "source": "crossref",
            },
            {
                "doi": "10.1000/xyz3",
                "title": "A third publication",
                "year": 2023,
                "journal": "Other Journal",
                "source": "crossref",
            },
        ]


class FundingTest(APIViewTestCases.APIViewTestCase):
    model = Funding
    brief_fields = ["award_number", "display", "funding_agency", "id", "title", "url"]
    bulk_update_data = {
        "status": "expired",
    }

    def model_to_dict(self, instance, fields, api=False):
        """Normalize django-money values to their numeric amount for comparison."""
        model_dict = super().model_to_dict(instance, fields, api=api)
        for key, value in list(model_dict.items()):
            if isinstance(value, Money):
                model_dict[key] = value.amount
        return model_dict

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        projects = (
            Project.objects.create(name="Project 1", owner=owner),
            Project.objects.create(name="Project 2", owner=owner),
            Project.objects.create(name="Project 3", owner=owner),
        )

        fundings = (
            Funding.objects.create(award_number="Award-1", funding_agency="NSF", title="Funding 1", source="nsf"),
            Funding.objects.create(award_number="Award-2", funding_agency="NSF", title="Funding 2", source="nsf"),
            Funding.objects.create(award_number="Award-3", funding_agency="NSF", title="Funding 3", source="nsf"),
        )
        fundings[0].projects.add(projects[0])
        fundings[1].projects.add(projects[0], projects[1])
        fundings[2].projects.add(projects[0], projects[1], projects[2])

        cls.create_data = [
            {
                "award_number": "Award-X1",
                "funding_agency": "NIH",
                "title": "A new funding",
                "amount_awarded": Decimal("10000.00"),
                "start_date": date(2024, 1, 1),
                "end_date": date(2025, 1, 1),
                "status": "active",
                "source": "nsf",
            },
            {
                "award_number": "Award-X2",
                "funding_agency": "NIH",
                "title": "Another funding",
                "amount_awarded": Decimal("20000.00"),
                "start_date": date(2024, 1, 1),
                "end_date": date(2025, 1, 1),
                "status": "active",
                "source": "nsf",
            },
            {
                "award_number": "Award-X3",
                "funding_agency": "NSF",
                "title": "A third funding",
                "amount_awarded": Decimal("30000.00"),
                "start_date": date(2024, 1, 1),
                "end_date": date(2025, 1, 1),
                "status": "expired",
                "source": "nsf",
            },
        ]
