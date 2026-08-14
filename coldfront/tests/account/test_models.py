# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import IntegrityError
from django.test import TestCase

from coldfront.account.models import ThirdPartyAccount
from coldfront.users.models import User


class ThirdPartyAccountModelTestCase(TestCase):
    """Tests for the ThirdPartyAccount model."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username="user1")
        cls.user2 = User.objects.create_user(username="user2")

    def create_account(self, user, provider="orcid", account_id="0000-0000-0000-0000"):
        return ThirdPartyAccount.objects.create(user=user, provider=provider, account_id=account_id)

    def test_create_third_party_account(self):
        account = self.create_account(self.user1)

        self.assertEqual(account.user, self.user1)
        self.assertEqual(account.provider, "orcid")
        self.assertEqual(account.account_id, "0000-0000-0000-0000")
        # Defaults
        self.assertFalse(account.is_verified)
        self.assertEqual(account.scopes, [])
        self.assertIsNotNone(account.linked_at)
        self.assertIsNone(account.last_synced_at)

        self.assertEqual(str(account), "orcid:0000-0000-0000-0000")

    def test_global_uniqueness_provider_account(self):
        """The same (provider, account_id) may only be linked to one account."""
        self.create_account(self.user1)

        with self.assertRaises(IntegrityError):
            self.create_account(self.user2)

    def test_user_provider_uniqueness(self):
        """A user may only link one account per provider."""
        self.create_account(self.user1)

        with self.assertRaises(IntegrityError):
            self.create_account(self.user1, account_id="0000-0000-0000-0001")

    def test_same_provider_different_accounts_allowed(self):
        """Different account_ids for the same provider are allowed on different users."""
        self.create_account(self.user1)
        self.create_account(self.user2, account_id="0000-0000-0000-0001")

        self.assertEqual(ThirdPartyAccount.objects.filter(provider="orcid").count(), 2)

    def test_different_providers_same_user_allowed(self):
        """A user may link accounts to different providers."""
        self.create_account(self.user1)
        self.create_account(self.user1, provider="other", account_id="abc")

        self.assertEqual(ThirdPartyAccount.objects.filter(user=self.user1).count(), 2)

    def test_user_cascade_delete(self):
        """Deleting a user removes their third-party account links."""
        account = self.create_account(self.user1)
        self.user1.delete()
        self.assertFalse(ThirdPartyAccount.objects.filter(pk=account.pk).exists())

    def test_related_name(self):
        account = self.create_account(self.user1)
        self.assertEqual(list(self.user1.third_party_accounts.all()), [account])
