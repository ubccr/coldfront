# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

from django.test import TestCase

from coldfront.ris.plugins.crossref.client import CrossrefClient, CrossrefError

CROSSREF_SEARCH = {
    "message": {
        "items": [
            {
                "DOI": "10.1000/aaa",
                "title": ["A First Paper"],
                "author": [
                    {"given": "Jane", "family": "Doe", "ORCID": "0000-0000-0000-0000"},
                    {"given": "John", "family": "Smith"},
                ],
                "published": {"date-parts": [[2024, 5, 20]]},
                "container-title": ["Journal of Tests"],
            },
            {
                "DOI": "10.1000/bbb",
                "title": ["A Second Paper"],
                "author": [],
                "published": {"date-parts": [[2023]]},
                "container-title": [],
            },
            {
                # No DOI: must be dropped.
                "title": ["No DOI Paper"],
                "published": {"date-parts": [[2022]]},
                "container-title": ["Another Journal"],
            },
        ]
    }
}


class CrossrefClientTestCase(TestCase):
    """Tests for the Crossref API-only provider client."""

    def make_client(self):
        return CrossrefClient(config={})

    @mock.patch("habanero.Crossref.works")
    def test_search_works_parses_results(self, works):
        works.return_value = CROSSREF_SEARCH

        pubs = self.make_client().search_works("paper")

        self.assertEqual(len(pubs), 2)
        self.assertEqual(pubs[0].doi, "10.1000/aaa")
        self.assertEqual(pubs[0].title, "A First Paper")
        self.assertEqual(pubs[0].year, 2024)
        self.assertEqual(pubs[0].journal, "Journal of Tests")
        self.assertEqual(pubs[0].source, "crossref")
        self.assertEqual(
            pubs[0].authors,
            [
                {"name": "Jane Doe", "orcid": "0000-0000-0000-0000"},
                {"name": "John Smith", "orcid": None},
            ],
        )
        self.assertEqual(pubs[1].year, 2023)
        self.assertEqual(pubs[1].authors, [])

        # No-DOI records are dropped.
        self.assertNotIn("No DOI Paper", [p.title for p in pubs])

    @mock.patch("habanero.Crossref.works")
    def test_search_works_passes_query_and_select(self, works):
        works.return_value = {"message": {"items": []}}

        self.make_client().search_works("two words")

        self.assertEqual(works.call_args.kwargs["query"], "two words")
        self.assertEqual(works.call_args.kwargs["limit"], 50)
        self.assertEqual(
            works.call_args.kwargs["select"],
            ["DOI", "title", "author", "published", "container-title"],
        )

    @mock.patch("habanero.Crossref.works")
    def test_fetch_work_by_doi(self, works):
        # A single-DOI fetch returns message-type "work" where ``message`` IS
        # the work dict (not wrapped in ``message.items`` like a search). The
        # single-work endpoint also rejects ``select`` (HTTP 400), so no select
        # must be sent.
        works.return_value = {
            "message-type": "work",
            "message": {
                "DOI": "10.1000/aaa",
                "title": ["A First Paper"],
                "published": {"date-parts": [[2024]]},
                "container-title": ["Journal of Tests"],
            },
        }

        pubs = self.make_client().fetch_work(["10.1000/aaa"])

        self.assertEqual(len(pubs), 1)
        pub = pubs[0]
        self.assertEqual(pub.doi, "10.1000/aaa")
        self.assertEqual(pub.title, "A First Paper")
        self.assertEqual(pub.year, 2024)
        self.assertEqual(pub.journal, "Journal of Tests")
        self.assertEqual(pub.source, "crossref")
        self.assertEqual(pub.external_id, "10.1000/aaa")
        self.assertEqual(works.call_args.kwargs["ids"], ["10.1000/aaa"])
        self.assertEqual(works.call_args.kwargs["warn"], True)
        self.assertNotIn("select", works.call_args.kwargs)

    @mock.patch("habanero.Crossref.works")
    def test_fetch_work_batches_multiple_dois(self, works):
        # Multiple DOIs are requested in a single call; habanero returns one
        # response dict per DOI (message-type "work"). A failed DOI maps to
        # None (``warn=True``).
        works.return_value = [
            {
                "message-type": "work",
                "message": {
                    "DOI": "10.1000/aaa",
                    "title": ["First Paper"],
                    "published": {"date-parts": [[2024]]},
                    "container-title": ["Journal A"],
                },
            },
            {
                "message-type": "work",
                "message": {
                    "DOI": "10.1000/bbb",
                    "title": ["Second Paper"],
                    "published": {"date-parts": [[2023]]},
                    "container-title": ["Journal B"],
                },
            },
        ]

        pubs = self.make_client().fetch_work(["10.1000/aaa", "10.1000/bbb"])

        self.assertEqual([p.doi for p in pubs], ["10.1000/aaa", "10.1000/bbb"])
        self.assertEqual([p.title for p in pubs], ["First Paper", "Second Paper"])
        self.assertEqual(works.call_args.kwargs["ids"], ["10.1000/aaa", "10.1000/bbb"])
        self.assertEqual(works.call_args.kwargs["warn"], True)

    @mock.patch("habanero.Crossref.works")
    def test_fetch_work_failed_doi_maps_to_none(self, works):
        works.return_value = [None]

        pubs = self.make_client().fetch_work(["10.1000/missing"])

        self.assertEqual(len(pubs), 1)
        self.assertIsNone(pubs[0])

    @mock.patch("habanero.Crossref.works")
    def test_http_error_raises(self, works):
        from habanero.exceptions import RequestError

        works.side_effect = RequestError(500, "boom")

        with self.assertRaises(CrossrefError):
            self.make_client().search_works("paper")
