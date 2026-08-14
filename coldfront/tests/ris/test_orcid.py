# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from coldfront.account.models import ThirdPartyAccount
from coldfront.ris.providers.orcid import views
from coldfront.ris.providers.orcid.client import ORCIDClient
from coldfront.users.models import User

ORCID_CONFIG = {"client_id": "test-client", "client_secret": "test-secret"}

VALID_ORCID = "0000-0000-0000-0000"


@override_settings(PLUGINS_CONFIG={"coldfront.ris.providers.orcid": ORCID_CONFIG})
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


@override_settings(PLUGINS_CONFIG={"coldfront.ris.providers.orcid": ORCID_CONFIG})
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


ORCID_WORKS = {
    "works": {
        "work": [
            {
                "work": {
                    "external_ids": {"external_id": [{"external_id_type": "doi", "external_id_value": "10.1000/aaa"}]},
                    "title": {"title": {"value": "A DOI Work"}},
                    "publication-date": {"year": {"value": 2024}},
                    "journal-title": {"title": {"value": "Journal of Tests"}},
                }
            },
            {
                "work": {
                    "title": {"title": {"value": "No DOI Work"}},
                    "publication-date": {"year": {"value": 2023}},
                }
            },
        ]
    }
}

ORCID_FUNDINGS = {
    "fundings": {
        "funding": [
            {
                "funding": {
                    "external_ids": {
                        "external_id": [{"external_id_type": "grant_number", "external_id_value": "Award-1"}]
                    },
                    "organization": {"name": {"value": "NSF"}},
                    "title": {"title": {"value": "A Funded Study"}},
                    "start-date": {"year": {"value": 2024}},
                    "end-date": {"year": {"value": 2026}},
                }
            },
            {
                "funding": {
                    "title": {"title": {"value": "No Award Funding"}},
                }
            },
        ]
    }
}


@override_settings(PLUGINS_CONFIG={"coldfront.ris.providers.orcid": ORCID_CONFIG})
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

        self.assertEqual(len(pubs), 1)
        self.assertEqual(pubs[0].doi, "10.1000/aaa")
        self.assertEqual(pubs[0].title, "A DOI Work")
        self.assertEqual(pubs[0].year, 2024)
        self.assertEqual(pubs[0].journal, "Journal of Tests")
        self.assertEqual(pubs[0].source, "orcid")

    def test_fetch_fundings(self):
        client = self.make_client()
        with mock.patch.object(client, "_request", return_value=ORCID_FUNDINGS):
            fundings = client.fetch_fundings(VALID_ORCID)

        self.assertEqual(len(fundings), 1)
        self.assertEqual(fundings[0].award_number, "Award-1")
        self.assertEqual(fundings[0].funding_agency, "NSF")
        self.assertEqual(fundings[0].title, "A Funded Study")
        self.assertEqual(str(fundings[0].start_date), "2024-01-01")
        self.assertEqual(fundings[0].source, "orcid")

    def test_fetch_works_drops_no_doi(self):
        client = self.make_client()
        with mock.patch.object(client, "_request", return_value=ORCID_WORKS):
            pubs = client.fetch_works(VALID_ORCID)
        self.assertNotIn("No DOI Work", [p.title for p in pubs])

    def test_fetch_work_by_put_codes(self):
        client = self.make_client()
        detail = {
            "external_ids": {"external_id": [{"external_id_type": "doi", "external_id_value": "10.1000/aaa"}]},
            "title": {"title": {"value": "Detail Work"}},
            "publication-date": {"year": {"value": 2024}},
            "journal-title": {"title": {"value": "Journal of Tests"}},
            "contributors": {"contributor": [{"contributor_orcid": {"path": "0000-1111-2222-3333"}}]},
        }
        with mock.patch.object(client, "_request", return_value=detail) as req:
            pubs = client.fetch_work(VALID_ORCID, [101, 102])

        self.assertEqual(len(pubs), 2)
        self.assertEqual([p.doi for p in pubs], ["10.1000/aaa", "10.1000/aaa"])
        self.assertEqual([p.external_id for p in pubs], [101, 102])
        self.assertEqual([p.source for p in pubs], ["orcid", "orcid"])
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
