# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import date
from unittest import mock

from django.urls import reverse

from coldfront.account.models import ThirdPartyAccount
from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication
from coldfront.users.models import User
from coldfront.utils.testing import TestCase as ColdFrontTestCase
from coldfront.utils.testing import ViewTestCases
from coldfront.utils.testing.utils import disable_warnings


class PublicationViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Publication

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

        cls.form_data = {
            "doi": "10.1000/xyz",
            "title": "A new publication",
            "year": 2024,
            "journal": "Test Journal",
            "authors": '[{"name": "Jane Doe"}]',
            "projects": [projects[0].pk, projects[1].pk],
        }

        cls.csv_data = (
            "doi,title,year,journal,source,projects",
            "10.1000/csv1,Fourth publication,2020,Journal 4,crossref,Project 1",
            "10.1000/csv2,Fifth publication,2021,Journal 5,crossref,Project 2",
            "10.1000/csv3,Sixth publication,2022,Journal 6,crossref,Project 3",
        )

        cls.csv_update_data = (
            "id,title",
            f"{publications[0].pk},Fourth publication7",
            f"{publications[1].pk},Fifth publication8",
            f"{publications[2].pk},Sixth publication9",
        )

        cls.bulk_edit_form_data = {
            "title": "Updated publication",
        }


class FundingViewTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Funding

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

        cls.form_data = {
            "award_number": "Award-X",
            "funding_agency": "NIH",
            "title": "A new funding",
            "amount_awarded_0": "10000.00",
            "amount_awarded_1": "USD",
            "start_date": date(2024, 1, 1),
            "end_date": date(2025, 1, 1),
            "status": "active",
            "projects": [projects[0].pk, projects[1].pk],
        }

        cls.csv_data = (
            "award_number,funding_agency,title,amount_awarded,start_date,end_date,status,source,projects",
            "Award-4,NIH,Fourth funding,10000.00,2020-01-01,2021-01-01,active,nsf,Project 1",
            "Award-5,NIH,Fifth funding,20000.00,2021-01-01,2022-01-01,active,nsf,Project 2",
            "Award-6,NIH,Sixth funding,30000.00,2022-01-01,2023-01-01,active,nsf,Project 3",
        )

        cls.csv_update_data = (
            "id,title",
            f"{fundings[0].pk},Fourth funding7",
            f"{fundings[1].pk},Fifth funding8",
            f"{fundings[2].pk},Sixth funding9",
        )

        cls.bulk_edit_form_data = {
            "title": "Updated funding",
        }


class ProjectPublicationTabViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.view_project", "ris.view_publication")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.pub = Publication.objects.create(doi="10.1000/aaa", title="Publication 1", source="crossref")
        self.pub.projects.add(self.project)

    def test_tab_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_tab_lists_linked_publications(self):
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publication 1")
        self.assertContains(response, "10.1000/aaa")

    def test_extra_controls_requires_permission(self):
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        # Without ras.change_project the Add Publication button is hidden.
        self.assertNotContains(response, "Add Publication")

    def test_extra_controls_with_permission(self):
        self.add_permissions("ras.change_project")
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Publication")

    def test_unlink_button_requires_permission(self):
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        # Without ris.unlink_publication the Remove Selected button is hidden.
        self.assertNotContains(response, "Remove Selected")

    def test_unlink_button_with_permission(self):
        self.add_permissions("ris.unlink_publication")
        response = self.client.get(reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remove Selected")


class ProjectFundingTabViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.view_project", "ris.view_funding")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.funding = Funding.objects.create(
            award_number="Award-1", funding_agency="NSF", title="Funding 1", source="nsf"
        )
        self.funding.projects.add(self.project)

    def test_tab_lists_linked_funding(self):
        response = self.client.get(reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Funding 1")
        self.assertContains(response, "Award-1")

    def test_extra_controls_requires_permission(self):
        response = self.client.get(reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Add Funding")

    def test_extra_controls_with_permission(self):
        self.add_permissions("ras.change_project")
        response = self.client.get(reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Funding")

    def test_unlink_button_requires_permission(self):
        response = self.client.get(reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        # Without ris.unlink_funding the Remove Selected button is hidden.
        self.assertNotContains(response, "Remove Selected")

    def test_unlink_button_with_permission(self):
        self.add_permissions("ris.unlink_funding")
        response = self.client.get(reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remove Selected")


class ProjectPublicationBulkUnlinkViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.view_project", "ris.view_publication", "ris.unlink_publication")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.other_project = Project.objects.create(name="Project 2", owner=self.user)
        self.pub = Publication.objects.create(doi="10.1000/aaa", title="Publication 1", source="crossref")
        self.pub2 = Publication.objects.create(doi="10.1000/bbb", title="Publication 2", source="crossref")
        self.pub.projects.add(self.project)
        self.pub2.projects.add(self.project, self.other_project)

    def test_unlink_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("ras:project_publication_bulk_unlink", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_unlink_requires_permission(self):
        self.remove_permissions("ris.unlink_publication")
        data = {"pk": [self.pub.pk], "confirm": True, "_confirm": True}
        with disable_warnings("django.request"):
            response = self.client.post(
                reverse("ras:project_publication_bulk_unlink", kwargs={"pk": self.project.pk}), data
            )
        self.assertEqual(response.status_code, 403)

    def test_unlink_shows_confirmation(self):
        response = self.client.post(
            reverse("ras:project_publication_bulk_unlink", kwargs={"pk": self.project.pk}),
            {"pk": [self.pub.pk], "confirm": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remove From Project")
        self.assertContains(response, "Publication 1")

    def test_unlink_removes_links_not_instances(self):
        response = self.client.post(
            reverse("ras:project_publication_bulk_unlink", kwargs={"pk": self.project.pk}),
            {"pk": [self.pub.pk, self.pub2.pk], "confirm": True, "_confirm": True},
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        # Both publications are unlinked from the current project.
        self.assertNotIn(self.pub, self.project.publications.all())
        self.assertNotIn(self.pub2, self.project.publications.all())
        # The global instances are not deleted.
        self.assertTrue(Publication.objects.filter(pk__in=[self.pub.pk, self.pub2.pk]).exists())
        # Other projects' links are preserved.
        self.assertEqual(list(self.other_project.publications.all()), [self.pub2])


class ProjectFundingBulkUnlinkViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.view_project", "ris.view_funding", "ris.unlink_funding")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.other_project = Project.objects.create(name="Project 2", owner=self.user)
        self.funding = Funding.objects.create(
            award_number="Award-1", funding_agency="NSF", title="Funding 1", source="nsf"
        )
        self.funding2 = Funding.objects.create(
            award_number="Award-2", funding_agency="NSF", title="Funding 2", source="nsf"
        )
        self.funding.projects.add(self.project)
        self.funding2.projects.add(self.project, self.other_project)

    def test_unlink_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("ras:project_funding_bulk_unlink", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_unlink_requires_permission(self):
        self.remove_permissions("ris.unlink_funding")
        data = {"pk": [self.funding.pk], "confirm": True, "_confirm": True}
        with disable_warnings("django.request"):
            response = self.client.post(
                reverse("ras:project_funding_bulk_unlink", kwargs={"pk": self.project.pk}), data
            )
        self.assertEqual(response.status_code, 403)

    def test_unlink_shows_confirmation(self):
        response = self.client.post(
            reverse("ras:project_funding_bulk_unlink", kwargs={"pk": self.project.pk}),
            {"pk": [self.funding.pk], "confirm": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remove From Project")
        self.assertContains(response, "Funding 1")

    def test_unlink_removes_links_not_instances(self):
        response = self.client.post(
            reverse("ras:project_funding_bulk_unlink", kwargs={"pk": self.project.pk}),
            {"pk": [self.funding.pk, self.funding2.pk], "confirm": True, "_confirm": True},
        )
        self.assertRedirects(response, reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        # Both fundings are unlinked from the current project.
        self.assertNotIn(self.funding, self.project.funding.all())
        self.assertNotIn(self.funding2, self.project.funding.all())
        # The global instances are not deleted.
        self.assertTrue(Funding.objects.filter(pk__in=[self.funding.pk, self.funding2.pk]).exists())
        # Other projects' links are preserved.
        self.assertEqual(list(self.other_project.funding.all()), [self.funding2])


class ProjectAddPublicationViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.change_project", "ras.view_project", "ris.view_publication")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.local_pub = Publication.objects.create(doi="10.1000/local", title="Local Publication", source="manual")

    def test_link_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    @mock.patch(
        "coldfront.ris.plugins.crossref.client.CrossrefClient.search",
        return_value=[Publication(doi="10.1000/xyz", title="Publication Crossref", year=2020, source="crossref")],
    )
    def test_get_renders_local_and_external_rows(self, search):
        """With a filter applied, local unlinked records and provider results are shown."""
        response = self.client.get(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"q": "Publication"},
        )
        self.assertEqual(response.status_code, 200)
        # Local, unlinked record appears with a local badge.
        self.assertContains(response, "Local Publication")
        self.assertContains(response, "local")
        # Provider result appears.
        self.assertContains(response, "Publication Crossref")
        # The filter/search form is rendered with its fields.
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'name="doi"')
        self.assertContains(response, 'name="author"')
        search.assert_called_once()

    def test_local_search_is_not_view_restricted(self):
        """A user without ris.view_publication can still search all local records."""
        self.remove_permissions("ris.view_publication")
        response = self.client.get(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"q": "Local"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Local Publication")
        self.assertContains(response, "local")

    def test_local_search_filters_author_at_the_database(self):
        """The author filter is applied at the DB level (not in Python)."""
        self.local_pub.authors = [{"name": "Alice Smith"}]
        self.local_pub.save()
        Publication.objects.create(doi="10.1000/other", title="Other", source="manual")
        response = self.client.get(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"author": "Smith"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Local Publication")
        self.assertNotContains(response, "Other")

    def test_get_default_shows_only_linked_provider_records(self):
        """With no filter, only the linked provider's records are shown (no local)."""
        ThirdPartyAccount.objects.create(user=self.user, provider="orcid", account_id="0000-0000")
        self.local_pub.projects.add(self.project)
        with mock.patch(
            "coldfront.ris.plugins.orcid.client.ORCIDClient.fetch_works",
            return_value=[Publication(doi="10.1000/orcid", title="Orcid Publication", year=2020, source="orcid")],
        ):
            response = self.client.get(reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Orcid Publication")
        self.assertNotContains(response, "Local Publication")
        # No Crossref-sourced result rows (the "Crossref" provider badge is
        # always shown, but no crossref candidate rows appear without a filter).
        self.assertNotContains(response, "crossref")

    def test_empty_state_when_no_rows(self):
        """With no local records and no search, an empty state is shown."""
        # Link the only local record to the project so it is excluded from the candidates.
        self.local_pub.projects.add(self.project)
        response = self.client.get(reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        # The shared table component renders the uniform empty state.
        self.assertContains(response, "card-body text-muted")

    @mock.patch(
        "coldfront.ris.plugins.crossref.client.CrossrefClient.search",
        return_value=[Publication(doi="10.1000/xyz", title="Publication Crossref", year=2020, source="crossref")],
    )
    def test_get_htmx_returns_table_partial(self, search):
        """HTMX requests (quick search / filter) return only the table partial."""
        response = self.client.get(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"q": "Publication"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Table rows are present, page chrome is not.
        self.assertIn("Publication Crossref", content)
        self.assertNotIn("Add Publications", content)
        self.assertNotIn('id="object-list-tab"', content)
        self.assertNotIn("Link Selected", content)
        search.assert_called_once()

    def test_link_local_record(self):
        response = self.client.post(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"pk": [f"local:{self.local_pub.pk}"]},
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(list(self.project.publications.all()), [self.local_pub])

    @mock.patch(
        "coldfront.ris.plugins.crossref.client.CrossrefClient.fetch_work",
        return_value=[
            Publication(
                doi="10.1000/xyz",
                title="Fetched Title",
                year=2020,
                journal="Fetched Journal",
                source="crossref",
            )
        ],
    )
    def test_link_external_record_creates(self, fetch):
        response = self.client.post(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"pk": ["external:crossref|10.1000/xyz|10.1000/xyz"]},
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        pub = Publication.objects.get(doi="10.1000/xyz")
        # Full provider metadata is preserved, not just the DOI.
        self.assertEqual(pub.title, "Fetched Title")
        self.assertEqual(pub.year, 2020)
        self.assertEqual(pub.journal, "Fetched Journal")
        self.assertEqual(pub.source, "crossref")
        self.assertEqual(pub.external_id, "10.1000/xyz")
        self.assertEqual(list(self.project.publications.all()), [pub])

    @mock.patch(
        "coldfront.ris.plugins.crossref.client.CrossrefClient.fetch_work",
        return_value=[None],
    )
    def test_link_external_record_fallback_when_refetch_fails(self, fetch):
        """When the provider cannot be re-fetched, the record is still created with its DOI."""
        response = self.client.post(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {"pk": ["external:crossref|10.1000/xyz|10.1000/xyz"]},
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        pub = Publication.objects.get(doi="10.1000/xyz")
        self.assertEqual(pub.source, "crossref")
        self.assertEqual(pub.external_id, "10.1000/xyz")
        self.assertEqual(list(self.project.publications.all()), [pub])

    @mock.patch(
        "coldfront.ris.plugins.crossref.client.CrossrefClient.fetch_work",
        return_value=[
            Publication(doi="10.1000/one", title="One", year=2020, source="crossref"),
            Publication(doi="10.1000/two", title="Two", year=2021, source="crossref"),
        ],
    )
    def test_link_multiple_external_records_batches_provider_call(self, fetch):
        """Selecting several external records results in a single provider call."""
        response = self.client.post(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {
                "pk": [
                    "external:crossref|10.1000/one|10.1000/one",
                    "external:crossref|10.1000/two|10.1000/two",
                ]
            },
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.args[0], ["10.1000/one", "10.1000/two"])
        self.assertEqual(
            sorted(p.doi for p in self.project.publications.all()),
            ["10.1000/one", "10.1000/two"],
        )

    def test_link_no_selection(self):
        response = self.client.post(
            reverse("ras:project_add_publication", kwargs={"pk": self.project.pk}),
            {},
        )
        self.assertRedirects(response, reverse("ras:project_publications", kwargs={"pk": self.project.pk}))
        self.assertEqual(self.project.publications.count(), 0)


class ProjectAddFundingViewTestCase(ColdFrontTestCase):
    user_permissions = ("ras.change_project", "ras.view_project", "ris.view_funding")

    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(name="Project 1", owner=self.user)
        self.local_funding = Funding.objects.create(
            award_number="Award-Local", funding_agency="NSF", title="Local Funding", source="manual"
        )

    @mock.patch(
        "coldfront.ris.plugins.nsf.client.NSFClient.search",
        return_value=[
            Funding(
                award_number="Award-N",
                funding_agency="NSF",
                title="Funding NSF",
                status="active",
                source="nsf",
            )
        ],
    )
    def test_get_renders_rows(self, search):
        """With a filter applied, local unlinked records and provider results are shown."""
        response = self.client.get(
            reverse("ras:project_add_funding", kwargs={"pk": self.project.pk}),
            {"q": "Funding"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Local Funding")
        self.assertContains(response, "local")
        self.assertContains(response, "Funding NSF")
        # The filter/search form is rendered with its fields.
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'name="award_number"')
        self.assertContains(response, 'name="funding_agency"')
        search.assert_called_once()

    def test_link_local_record(self):
        response = self.client.post(
            reverse("ras:project_add_funding", kwargs={"pk": self.project.pk}),
            {"pk": [f"local:{self.local_funding.pk}"]},
        )
        self.assertRedirects(response, reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        self.assertEqual(list(self.project.funding.all()), [self.local_funding])

    @mock.patch(
        "coldfront.ris.plugins.nsf.client.NSFClient.fetch_funding",
        return_value=[
            Funding(
                award_number="Award-X",
                funding_agency="NIH",
                title="Fetched Funding",
                status="active",
                source="nsf",
            )
        ],
    )
    def test_link_external_record_creates(self, fetch):
        response = self.client.post(
            reverse("ras:project_add_funding", kwargs={"pk": self.project.pk}),
            {"pk": ["external:nsf|12345|Award-X|NIH"]},
        )
        self.assertRedirects(response, reverse("ras:project_funding", kwargs={"pk": self.project.pk}))
        funding = Funding.objects.get(award_number="Award-X", funding_agency="NIH")
        # Full provider metadata is preserved, not just the award number.
        self.assertEqual(funding.title, "Fetched Funding")
        self.assertEqual(funding.status, "active")
        self.assertEqual(funding.source, "nsf")
        self.assertEqual(funding.external_id, "12345")
        self.assertEqual(list(self.project.funding.all()), [funding])
