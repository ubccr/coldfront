# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.urls import reverse

from coldfront.account.models import ThirdPartyAccount
from coldfront.registry import get_thirdparty_account, get_thirdparty_accounts, register_thirdparty_account
from coldfront.utils.testing import TestCase as ColdFrontTestCase


class ThirdPartyAccountRegistryTestCase(TestCase):
    """Tests for the third-party account registry."""

    def setUp(self):
        from coldfront.registry import registry

        self._original = dict(registry["third_party_accounts"])
        registry["third_party_accounts"].clear()

    def tearDown(self):
        from coldfront.registry import registry

        registry["third_party_accounts"].clear()
        registry["third_party_accounts"].update(self._original)

    def test_register(self):
        register_thirdparty_account(
            "orcid",
            display_name="ORCID",
            link_url="orcid:link",
            callback_url="orcid:callback",
            unlink_url="orcid:unlink",
        )
        meta = get_thirdparty_account("orcid")
        self.assertEqual(meta["key"], "orcid")
        self.assertEqual(meta["display_name"], "ORCID")
        self.assertEqual(meta["link_url"], "orcid:link")
        self.assertEqual(meta["callback_url"], "orcid:callback")
        self.assertEqual(meta["unlink_url"], "orcid:unlink")

    def test_duplicate_key_raises(self):
        register_thirdparty_account("orcid", display_name="ORCID", link_url="a", callback_url="b", unlink_url="c")
        with self.assertRaises(ValueError):
            register_thirdparty_account("orcid", display_name="ORCID", link_url="a", callback_url="b", unlink_url="c")

    def test_invalid_key_raises(self):
        with self.assertRaises(ValueError):
            register_thirdparty_account("", display_name="ORCID", link_url="a", callback_url="b", unlink_url="c")

    def test_missing_display_name_raises(self):
        with self.assertRaises(ValueError):
            register_thirdparty_account("orcid", display_name="", link_url="a", callback_url="b", unlink_url="c")

    def test_partial_urls_raise(self):
        with self.assertRaises(ValueError):
            register_thirdparty_account("orcid", display_name="ORCID", link_url="a", callback_url="b", unlink_url="")

    def test_get_thirdparty_accounts(self):
        register_thirdparty_account("orcid", display_name="ORCID", link_url="a", callback_url="b", unlink_url="c")
        providers = get_thirdparty_accounts()
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]["key"], "orcid")

    def test_get_thirdparty_account_unregistered(self):
        self.assertIsNone(get_thirdparty_account("missing"))


class ThirdPartyAccountsViewTestCase(ColdFrontTestCase):
    """Tests for the shared Third-Party Accounts page."""

    def setUp(self):
        super().setUp()
        from coldfront.registry import registry

        self._original = dict(registry["third_party_accounts"])
        registry["third_party_accounts"].clear()

    def tearDown(self):
        from coldfront.registry import registry

        registry["third_party_accounts"].clear()
        registry["third_party_accounts"].update(self._original)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("account:third_party_accounts"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_empty_state(self):
        """With no providers configured the page renders a friendly empty state."""
        response = self.client.get(reverse("account:third_party_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No third-party providers are configured.")
        # The nav tab is hidden when no providers are registered.
        self.assertNotContains(response, 'href="/user/third-party-accounts/"')

    def test_renders_provider(self):
        register_thirdparty_account(
            "orcid",
            display_name="ORCID",
            link_url="account:profile",
            callback_url="account:profile",
            unlink_url="account:profile",
        )
        response = self.client.get(reverse("account:third_party_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ORCID")
        self.assertContains(response, "Link ORCID")
        # The nav tab is rendered when at least one provider is registered.
        self.assertContains(response, 'href="/user/third-party-accounts/"')

    def test_renders_linked_account(self):
        register_thirdparty_account(
            "orcid",
            display_name="ORCID",
            link_url="account:profile",
            callback_url="account:profile",
            unlink_url="account:profile",
        )
        ThirdPartyAccount.objects.create(user=self.user, provider="orcid", account_id="0000-0000-0000-0000")
        response = self.client.get(reverse("account:third_party_accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0000-0000-0000-0000")
        self.assertContains(response, "Unlink")
