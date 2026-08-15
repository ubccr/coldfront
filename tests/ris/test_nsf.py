# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import date
from unittest import mock

from django.test import TestCase

from coldfront.ris.plugins.nsf.client import NSFClient

NSF_SEARCH = {
    "response": {
        "award": [
            {
                "id": 1234567,
                "title": "A Water Study",
                "agency": "NSF",
                "estimatedTotalAmt": 250000.0,
                "startDate": "01/01/2024",
                "expDate": "12/31/2026",
                "activeAwd": True,
            },
            {
                "id": 7654321,
                "title": "An Expired Study",
                "agency": "NSF",
                "estimatedTotalAmt": 10000.0,
                "startDate": "01/01/2020",
                "expDate": "12/31/2022",
                "activeAwd": False,
            },
            {
                # Missing agency: must be dropped.
                "id": 9999999,
                "title": "No Agency Award",
                "estimatedTotalAmt": 5000.0,
            },
        ]
    }
}


class NSFClientTestCase(TestCase):
    """Tests for the NSF Awards API-only provider client."""

    def make_client(self):
        return NSFClient(config={})

    @mock.patch("requests.get")
    def test_search_fundings_parses_results(self, get):
        get.return_value.json.return_value = NSF_SEARCH
        get.return_value.status_code = 200

        fundings = self.make_client().search_fundings("water")

        self.assertEqual(len(fundings), 2)
        self.assertEqual(fundings[0].award_number, "1234567")
        self.assertEqual(fundings[0].funding_agency, "NSF")
        self.assertEqual(fundings[0].title, "A Water Study")
        self.assertEqual(str(fundings[0].start_date), "2024-01-01")
        self.assertEqual(str(fundings[0].end_date), "2026-12-31")
        self.assertEqual(str(fundings[0].amount_awarded.amount), "250000.00")
        self.assertEqual(fundings[0].amount_awarded_currency, "USD")
        self.assertEqual(fundings[0].status, "active")
        self.assertEqual(fundings[0].source, "nsf")
        self.assertEqual(fundings[1].status, "expired")

        # Awards missing agency are dropped.
        self.assertNotIn("No Agency Award", [f.title for f in fundings])

    @mock.patch("requests.get")
    def test_search_fundings_quotes_query(self, get):
        get.return_value.json.return_value = {"response": {"award": []}}
        get.return_value.status_code = 200

        self.make_client().search_fundings("two words")

        url = get.call_args.args[0]
        self.assertIn("keyword=two%20words", url)

    @mock.patch("requests.get")
    def test_fetch_funding_by_id(self, get):
        # The NSF API wraps even a single award in a ``response.award`` list.
        get.return_value.json.return_value = {
            "response": {
                "award": [
                    {
                        "id": 1234567,
                        "title": "A Water Study",
                        "agency": "NSF",
                        "estimatedTotalAmt": 250000.0,
                        "startDate": "01/01/2024",
                        "expDate": "12/31/2026",
                        "activeAwd": True,
                    }
                ]
            }
        }
        get.return_value.status_code = 200

        fundings = self.make_client().fetch_funding([1234567])

        self.assertEqual(len(fundings), 1)
        funding = fundings[0]
        self.assertEqual(funding.award_number, "1234567")
        self.assertEqual(funding.funding_agency, "NSF")
        self.assertEqual(funding.title, "A Water Study")
        self.assertEqual(str(funding.amount_awarded.amount), "250000.00")
        self.assertEqual(funding.amount_awarded_currency, "USD")
        self.assertEqual(funding.start_date, date(2024, 1, 1))
        self.assertEqual(funding.end_date, date(2026, 12, 31))
        self.assertEqual(funding.status, "active")
        self.assertEqual(funding.source, "nsf")
        self.assertEqual(funding.external_id, "1234567")

    @mock.patch("requests.get")
    def test_fetch_funding_fetches_each_award(self, get):
        # NSF has no multi-award endpoint: each award id is fetched with its own
        # request, and results stay aligned with the input ids.
        def _response(url, **kwargs):
            award_id = int(url.split("/awards/")[1].split(".json")[0])
            resp = mock.Mock()
            resp.status_code = 200
            resp.json.return_value = {
                "response": {"award": [{"id": award_id, "title": "Award", "agency": "NSF", "activeAwd": True}]}
            }
            return resp

        get.side_effect = _response

        fundings = self.make_client().fetch_funding([111, 222])

        self.assertEqual(len(fundings), 2)
        self.assertEqual([f.award_number for f in fundings], ["111", "222"])
        self.assertEqual(get.call_count, 2)

    @mock.patch("requests.get")
    def test_http_error_raises(self, get):
        get.return_value.status_code = 500
        get.return_value.json.return_value = {}

        with self.assertRaises(Exception):
            self.make_client().search_fundings("water")
