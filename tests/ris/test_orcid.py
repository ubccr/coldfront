# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from coldfront.account.models import ThirdPartyAccount
from coldfront.ris.plugins.orcid import views
from coldfront.ris.plugins.orcid.client import ORCIDClient
from coldfront.users.models import User

ORCID_CONFIG = {"client_id": "test-client", "client_secret": "test-secret"}

VALID_ORCID = "0000-0000-0000-0000"


@override_settings(PLUGINS_CONFIG={"coldfront.ris.plugins.orcid": ORCID_CONFIG})
class ORCIDClientTestCase(TestCase):
    """Tests for the self-contained ORCID client."""

    def make_client(self, **overrides):
        config = {"client_id": "cid", "client_secret": "secret", "base_url": "https://sandbox.orcid.org"}
        config.update(overrides)
        return ORCIDClient(config=config)

    def test_build_authorize_url(self):
        url = self.make_client().build_authorize_url("state123", "nonce456", "https://example.com/callback")
        self.assertIn("https://sandbox.orcid.org/oauth/authorize?", url)
        self.assertIn("client_id=cid", url)
        self.assertIn("scope=%2Fauthenticate", url)
        self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fcallback", url)
        self.assertIn("state=state123", url)
        self.assertIn("nonce=nonce456", url)

    def test_scope_default(self):
        self.assertEqual(self.make_client().scope, "/authenticate")

    def test_extract_orcid_id_valid(self):
        client = self.make_client()
        self.assertEqual(client.extract_orcid_id({"sub": VALID_ORCID}), VALID_ORCID)

    def test_extract_orcid_id_from_token_fallback(self):
        client = self.make_client()
        identity = {}
        token = {"orcid_identifier": {"path": VALID_ORCID}}
        self.assertEqual(client.extract_orcid_id(identity, token), VALID_ORCID)

    def test_extract_orcid_id_invalid(self):
        client = self.make_client()
        with self.assertRaises(ValueError):
            client.extract_orcid_id({"sub": "1234"})
        with self.assertRaises(ValueError):
            client.extract_orcid_id({})


@override_settings(PLUGINS_CONFIG={"coldfront.ris.plugins.orcid": ORCID_CONFIG})
class ORCIDProviderViewTestCase(TestCase):
    """Tests for the ORCID link-only flow."""

    def setUp(self):
        # ORCID is registered with the ris registry by the decorator on
        # ORCIDClient when it is imported above.
        self.user = User.objects.create_user(username="testuser")

    def set_session_state(self):
        session = self.client.session
        session["account_state_orcid"] = "expected-state"
        session.save()

    def link_callback(self, code="authcode", state="expected-state"):
        return self.client.get(reverse("plugins:orcid:callback"), {"code": code, "state": state})

    # Link view

    def test_link_requires_login(self):
        response = self.client.get(reverse("plugins:orcid:link"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_link_redirects_to_orcid(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("plugins:orcid:link"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("https://orcid.org/oauth/authorize", response.url)
        # State is stored in the session for the callback.
        self.assertIn("account_state_orcid", self.client.session)

    def test_link_already_linked(self):
        ThirdPartyAccount.objects.create(user=self.user, provider="orcid", account_id=VALID_ORCID)
        self.client.force_login(self.user)
        response = self.client.get(reverse("plugins:orcid:link"))
        self.assertRedirects(response, reverse("account:third_party_accounts"))
        self.assertNotIn("https://orcid.org", response.url)

    # Callback

    @mock.patch.object(
        views.ORCIDClient,
        "exchange_code",
        return_value={"access_token": "tok", "orcid_identifier": {"path": VALID_ORCID}},
    )
    @mock.patch.object(views.ORCIDClient, "fetch_identity", return_value={"sub": VALID_ORCID})
    def test_callback_links_verified_account(self, *args):
        self.client.force_login(self.user)
        self.set_session_state()
        response = self.link_callback()
        self.assertRedirects(response, reverse("account:third_party_accounts"))

        account = ThirdPartyAccount.objects.get(user=self.user, provider="orcid")
        self.assertEqual(account.account_id, VALID_ORCID)
        self.assertTrue(account.is_verified)
        # No-login invariant: no ColdFront user is created by the callback.
        self.assertEqual(User.objects.count(), 1)

    def test_callback_requires_login(self):
        response = self.link_callback()
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_callback_invalid_state(self):
        self.client.force_login(self.user)
        self.set_session_state()
        response = self.client.get(reverse("plugins:orcid:callback"), {"code": "x", "state": "wrong-state"})
        self.assertRedirects(response, reverse("account:third_party_accounts"))
        self.assertFalse(ThirdPartyAccount.objects.filter(user=self.user).exists())

    def test_callback_missing_code(self):
        self.client.force_login(self.user)
        self.set_session_state()
        response = self.client.get(reverse("plugins:orcid:callback"), {"state": "expected-state"})
        self.assertRedirects(response, reverse("account:third_party_accounts"))
        self.assertFalse(ThirdPartyAccount.objects.filter(user=self.user).exists())

    @mock.patch.object(views.ORCIDClient, "exchange_code", return_value={"access_token": "tok"})
    @mock.patch.object(views.ORCIDClient, "fetch_identity", return_value={"sub": VALID_ORCID})
    def test_callback_duplicate_orcid_rejected(self, *args):
        other = User.objects.create_user(username="other")
        ThirdPartyAccount.objects.create(user=other, provider="orcid", account_id=VALID_ORCID)

        self.client.force_login(self.user)
        self.set_session_state()
        response = self.link_callback()
        self.assertRedirects(response, reverse("account:third_party_accounts"))
        # Global uniqueness: the iD already belongs to another account.
        self.assertFalse(ThirdPartyAccount.objects.filter(user=self.user, provider="orcid").exists())

    # Unlink

    def test_unlink_removes_account(self):
        ThirdPartyAccount.objects.create(user=self.user, provider="orcid", account_id=VALID_ORCID)
        self.client.force_login(self.user)
        response = self.client.post(reverse("plugins:orcid:unlink"))
        self.assertRedirects(response, reverse("account:third_party_accounts"))
        self.assertFalse(ThirdPartyAccount.objects.filter(user=self.user).exists())

    def test_unlink_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("plugins:orcid:unlink"))
        self.assertEqual(response.status_code, 405)


# The real ORCID public API /works response.
ORCID_WORKS = {
    "group": [
        {
            "external-ids": {
                "external-id": [{"external-id-type": "doi", "external-id-value": "10.1371/journal.pone.0198883"}]
            },
            "work-summary": [
                {
                    "put-code": 2523615,
                    "title": {
                        "title": {
                            "value": "Classification of crystallization outcomes using deep convolutional neural networks"
                        }
                    },
                    "external-ids": {
                        "external-id": [
                            {"external-id-type": "doi", "external-id-value": "10.1371/journal.pone.0198883"},
                            {"external-id-type": "issn", "external-id-value": "1932-6203"},
                        ]
                    },
                    "url": {"value": "http://dx.doi.org/10.1371/journal.pone.0198883"},
                    "type": "journal-article",
                    "publication-date": {"year": {"value": "2018"}, "month": {"value": "06"}, "day": {"value": "20"}},
                    "journal-title": {"value": "PLOS ONE"},
                }
            ],
        },
        {
            "external-ids": {
                "external-id": [{"external-id-type": "doi", "external-id-value": "10.1107/s160057671601431x"}]
            },
            "work-summary": [
                {
                    "put-code": 2523616,
                    "title": {"title": {"value": "The use of haptic interfaces and web services in crystallography"}},
                    "external-ids": {
                        "external-id": [{"external-id-type": "doi", "external-id-value": "10.1107/s160057671601431x"}]
                    },
                    "url": {"value": "http://dx.doi.org/10.1107/s160057671601431x"},
                    "type": "journal-article",
                    "publication-date": {"year": {"value": "2016"}, "month": {"value": "12"}, "day": {"value": "01"}},
                    "journal-title": {"value": "Journal of Applied Crystallography"},
                }
            ],
        },
    ]
}

# The real ORCID public API /fundings response.
ORCID_FUNDINGS = {
    "group": [
        {
            "external-ids": {"external-id": [{"external-id-type": "grant_number", "external-id-value": "2517857"}]},
            "funding-summary": [
                {
                    "put-code": 19415,
                    "title": {
                        "title": {
                            "value": "POSE: Phase I: ColdFront: High Performance Computing (HPC) Community Allocation and Resource Ecosystem (HPC CARE)"
                        }
                    },
                    "external-ids": {
                        "external-id": [{"external-id-type": "grant_number", "external-id-value": "2517857"}]
                    },
                    "url": {"value": "https://app.dimensions.ai/details/grant/grant.15049493"},
                    "type": "grant",
                    "start-date": {"year": {"value": "2025"}, "month": {"value": "09"}, "day": {"value": "01"}},
                    "end-date": {"year": {"value": "2026"}, "month": {"value": "08"}, "day": {"value": "31"}},
                    "organization": {"name": "Directorate for Technology, Innovation and Partnerships"},
                }
            ],
        },
        {
            "external-ids": {"external-id": [{"external-id-type": "grant_number", "external-id-value": "2411376"}]},
            "funding-summary": [
                {
                    "put-code": 19417,
                    "title": {
                        "title": {
                            "value": "Collaborative Research: Frameworks: Growing Open OnDemand: Leveraging Unified Community Knowledge (GOODLUCK)"
                        }
                    },
                    "external-ids": {
                        "external-id": [{"external-id-type": "grant_number", "external-id-value": "2411376"}]
                    },
                    "url": {"value": "https://app.dimensions.ai/details/grant/grant.14347283"},
                    "type": "grant",
                    "start-date": {"year": {"value": "2024"}, "month": {"value": "09"}, "day": {"value": "01"}},
                    "end-date": {"year": {"value": "2029"}, "month": {"value": "08"}, "day": {"value": "31"}},
                    "organization": {"name": "Directorate for Computer & Information Science & Engineering"},
                }
            ],
        },
    ]
}


@override_settings(PLUGINS_CONFIG={"coldfront.ris.plugins.orcid": ORCID_CONFIG})
class ORCIDFetchTestCase(TestCase):
    """Tests for the ORCID public read API import methods."""

    def make_client(self):
        return ORCIDClient(config={"base_url": "https://sandbox.orcid.org"})

    def test_pub_base_url(self):
        self.assertEqual(self.make_client().pub_base_url, "https://pub.sandbox.orcid.org")
        self.assertEqual(ORCIDClient(config={"base_url": "https://orcid.org"}).pub_base_url, "https://pub.orcid.org")

    def test_fetch_works(self):
        client = self.make_client()
        with mock.patch.object(client, "_request", return_value=ORCID_WORKS):
            pubs = client.fetch_works(VALID_ORCID)

        self.assertEqual(len(pubs), 2)
        self.assertEqual([p.doi for p in pubs], ["10.1371/journal.pone.0198883", "10.1107/s160057671601431x"])
        self.assertEqual(
            [p.title for p in pubs],
            [
                "Classification of crystallization outcomes using deep convolutional neural networks",
                "The use of haptic interfaces and web services in crystallography",
            ],
        )
        self.assertEqual([p.year for p in pubs], [2018, 2016])
        self.assertEqual([p.journal for p in pubs], ["PLOS ONE", "Journal of Applied Crystallography"])
        self.assertEqual([p.external_id for p in pubs], ["2523615", "2523616"])
        self.assertEqual([p.source for p in pubs], ["orcid", "orcid"])

    def test_fetch_fundings(self):
        client = self.make_client()
        with mock.patch.object(client, "_request", return_value=ORCID_FUNDINGS):
            fundings = client.fetch_fundings(VALID_ORCID)

        self.assertEqual(len(fundings), 2)
        self.assertEqual([f.award_number for f in fundings], ["2517857", "2411376"])
        self.assertEqual(
            [f.funding_agency for f in fundings],
            [
                "Directorate for Technology, Innovation and Partnerships",
                "Directorate for Computer & Information Science & Engineering",
            ],
        )
        self.assertEqual(
            [f.title for f in fundings],
            [
                "POSE: Phase I: ColdFront: High Performance Computing (HPC) Community Allocation and Resource Ecosystem (HPC CARE)",
                "Collaborative Research: Frameworks: Growing Open OnDemand: Leveraging Unified Community Knowledge (GOODLUCK)",
            ],
        )
        self.assertEqual([str(f.start_date) for f in fundings], ["2025-09-01", "2024-09-01"])
        self.assertEqual([str(f.end_date) for f in fundings], ["2026-08-31", "2029-08-31"])
        self.assertEqual([f.external_id for f in fundings], ["19415", "19417"])
        self.assertEqual([f.source for f in fundings], ["orcid", "orcid"])

    def test_fetch_work_by_put_codes(self):
        client = self.make_client()
        detail = {
            "put-code": 2523616,
            "title": {"title": {"value": "The use of haptic interfaces and web services in crystallography"}},
            "journal-title": {"value": "Journal of Applied Crystallography"},
            "type": "journal-article",
            "publication-date": {"year": {"value": "2016"}, "month": {"value": "12"}, "day": {"value": "01"}},
            "external-ids": {
                "external-id": [
                    {"external-id-type": "doi", "external-id-value": "10.1107/s160057671601431x"},
                    {"external-id-type": "issn", "external-id-value": "1600-5767"},
                ]
            },
            "url": {"value": "http://dx.doi.org/10.1107/s160057671601431x"},
            "contributors": {
                "contributor": [
                    {
                        "contributor-orcid": {"uri": None, "path": None, "host": None},
                        "credit-name": {"value": "Andrew E. Bruno"},
                    },
                    {
                        "contributor-orcid": {
                            "uri": "https://sandbox.orcid.org/0000-0002-6565-8503",
                            "path": "0000-0002-6565-8503",
                        },
                        "credit-name": {"value": "Alexei S. Soares"},
                    },
                    {
                        "contributor-orcid": {
                            "uri": "https://sandbox.orcid.org/0000-0002-2104-7057",
                            "path": "0000-0002-2104-7057",
                        },
                        "credit-name": {"value": "Robin L. Owen"},
                    },
                    {
                        "contributor-orcid": {
                            "uri": "https://sandbox.orcid.org/0000-0001-8714-3191",
                            "path": "0000-0001-8714-3191",
                        },
                        "credit-name": {"value": "Edward H. Snell"},
                    },
                ]
            },
        }
        with mock.patch.object(client, "_request", return_value=detail) as req:
            pubs = client.fetch_work(VALID_ORCID, [101, 102])

        self.assertEqual(len(pubs), 2)
        self.assertEqual([p.doi for p in pubs], ["10.1107/s160057671601431x", "10.1107/s160057671601431x"])
        self.assertEqual([p.external_id for p in pubs], [101, 102])
        self.assertEqual([p.source for p in pubs], ["orcid", "orcid"])
        self.assertEqual(
            [a["name"] for a in pubs[0].authors],
            ["Andrew E. Bruno", "Alexei S. Soares", "Robin L. Owen", "Edward H. Snell"],
        )
        self.assertEqual(
            [a["orcid"] for a in pubs[0].authors],
            [None, "0000-0002-6565-8503", "0000-0002-2104-7057", "0000-0001-8714-3191"],
        )
        # ORCID has no multi-work endpoint: one request per put code.
        self.assertEqual(req.call_count, 2)

    def test_fetch_funding_by_put_codes(self):
        client = self.make_client()
        detail = {
            "external_ids": {"external_id": [{"external_id_type": "grant_number", "external_id_value": "Award-1"}]},
            "organization": {"name": {"value": "NSF"}},
            "title": {"title": {"value": "Detail Funding"}},
            "amount": {"amount": "250000.00", "currency_code": {"value": "USD"}},
            "start-date": {"year": {"value": 2024}},
            "end-date": {"year": {"value": 2026}},
        }
        with mock.patch.object(client, "_request", return_value=detail) as req:
            fundings = client.fetch_funding(VALID_ORCID, [201, 202])

        self.assertEqual(len(fundings), 2)
        self.assertEqual([f.award_number for f in fundings], ["Award-1", "Award-1"])
        self.assertEqual([f.external_id for f in fundings], [201, 202])
        self.assertEqual([f.source for f in fundings], ["orcid", "orcid"])
        # ORCID has no multi-funding endpoint: one request per put code.
        self.assertEqual(req.call_count, 2)
