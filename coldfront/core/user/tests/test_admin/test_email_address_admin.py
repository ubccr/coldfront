from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from coldfront.core.user.models import EmailAddress
from coldfront.core.user.admin import EmailAddressAdmin
from django.http import HttpRequest
from django.contrib.messages.storage import default_storage
from django.contrib.messages import get_messages


class EmailAddressAdminTest(TestCase):
    """
    Class for testing methods in EmailAddressAdmin
    """

    def setUp(self):
        """Set up test data."""
        self.app_admin = EmailAddressAdmin(EmailAddress, AdminSite())

        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='First',
            last_name='Last',
            username='user1')

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='First',
            last_name='Last',
            username='user2')

        self.email1 = EmailAddress.objects.create(
            user=self.user1,
            email='email1@email.com',
            is_verified=True,
            is_primary=True)

        self.email2 = EmailAddress.objects.create(
            user=self.user1,
            email='email2@email.com',
            is_verified=True,
            is_primary=False)

        self.email3 = EmailAddress.objects.create(
            user=self.user2,
            email='email3@email.com',
            is_verified=True,
            is_primary=True)

        self.email4 = EmailAddress.objects.create(
            user=self.user2,
            email='email4@email.com',
            is_verified=True,
            is_primary=False)

        self.email5 = EmailAddress.objects.create(
            user=self.user2,
            email='email5@email.com',
            is_verified=False,
            is_primary=False)

        self.request = HttpRequest()
        setattr(self.request, 'session', 'session')
        messages = default_storage(self.request)
        setattr(self.request, '_messages', messages)

    def test_delete_model_primary_email(self):
        """
        Testing EmailAddressAdmin delete_model method when email is primary
        """
        try:
            self.app_admin.delete_model(self.request, self.email1)
        except ValidationError as e:
            self.assertIn(
                f'Cannot delete primary email. Unset primary status in list '
                f'display before deleting.', str(e))
        else:
            self.fail('A ValidationError should have been raised.')

    def test_delete_model_non_primary_email(self):
        """
        Testing EmailAddressAdmin delete_model method when email is not primary
        """
        pk = self.email2.pk
        self.app_admin.delete_model(self.request, self.email2)
        self.assertFalse(EmailAddress.objects.filter(pk=pk).exists())

    def test_make_primary_multiple_emails(self):
        """
        Testing EmailAddressAdmin make_primary method with multiple emails
        """
        try:
            query_set = EmailAddress.objects.all()
            self.app_admin.make_primary(self.request, query_set)
        except ValidationError as e:
            self.assertIn(f'Cannot set more than one primary email address at '
                          f'a time.', str(e))
        else:
            self.fail('A ValidationError should have been raised.')

    def test_make_primary_single_unverified_email(self):
        """
        Testing EmailAddressAdmin make_primary method with single unverified email
        """
        try:
            query_set = EmailAddress.objects.filter(pk=self.email5.pk)
            self.app_admin.make_primary(self.request, query_set)
        except ValidationError as e:
            self.assertIn(f'Cannot set an unverified email address as '
                          f'primary.', str(e))
        else:
            self.fail('A ValidationError should have been raised.')

    def test_make_primary_single_primary_email(self):
        """
        Testing EmailAddressAdmin make_primary method with single primary email
        """
        query_set = EmailAddress.objects.filter(pk=self.email1.pk)
        self.app_admin.make_primary(self.request, query_set)
        self.email1.refresh_from_db()
        self.assertTrue(self.email1.is_primary)

        storage = list(get_messages(self.request))
        self.assertEqual(len(storage), 1)
        self.assertEqual(f'Set User {self.email1.user.pk}\'s '
                         f'primary EmailAddress to '
                         f'{self.email1.email}.', str(storage[0]))

    def test_make_primary_single_non_primary_email(self):
        """
        Testing EmailAddressAdmin make_primary method with single non primary email
        """
        query_set = EmailAddress.objects.filter(pk=self.email2.pk)
        self.app_admin.make_primary(self.request, query_set)
        self.email1.refresh_from_db()
        self.assertFalse(self.email1.is_primary)

        self.email2.refresh_from_db()
        self.assertTrue(self.email2.is_primary)

        storage = list(get_messages(self.request))
        self.assertEqual(len(storage), 1)
        self.assertEqual(f'Set User {self.email2.user.pk}\'s '
                         f'primary EmailAddress to '
                         f'{self.email2.email}.', str(storage[0]))

    def test_make_delete_queryset_only_primary(self):
        """
        Testing EmailAddressAdmin delete_queryset method with only primary emails
        """

        query_set = EmailAddress.objects.filter(is_primary=True)
        self.app_admin.delete_queryset(self.request, query_set)

        self.assertTrue(EmailAddress.objects.filter(pk=self.email1.pk).exists())
        self.assertTrue(EmailAddress.objects.filter(pk=self.email3.pk).exists())

        storage = list(get_messages(self.request))
        self.assertEqual(len(storage), 2)
        self.assertEqual(f'Deleted 0 non-primary EmailAddresses.',
                         str(storage[0]))
        self.assertEqual(f'Skipped deleting 2 primary EmailAddresses.',
                         str(storage[1]))

    def test_make_delete_queryset_only_non_primary(self):
        """
        Testing EmailAddressAdmin delete_queryset method with only non
        primary emails
        """

        query_set = EmailAddress.objects.filter(is_primary=False)
        self.app_admin.delete_queryset(self.request, query_set)

        self.assertFalse(EmailAddress.objects.filter(pk=self.email2.pk).exists())
        self.assertFalse(EmailAddress.objects.filter(pk=self.email4.pk).exists())
        self.assertFalse(EmailAddress.objects.filter(pk=self.email5.pk).exists())

        storage = list(get_messages(self.request))
        self.assertEqual(len(storage), 1)
        self.assertEqual(f'Deleted 3 non-primary EmailAddresses.',
                         str(storage[0]))

    def test_make_delete_queryset_mixed(self):
        """
        Testing EmailAddressAdmin delete_queryset method with only non
        primary emails
        """

        query_set = EmailAddress.objects.filter(user=self.user2)
        self.app_admin.delete_queryset(self.request, query_set)

        self.assertTrue(EmailAddress.objects.filter(pk=self.email3.pk).exists())
        self.assertFalse(EmailAddress.objects.filter(pk=self.email4.pk).exists())
        self.assertFalse(EmailAddress.objects.filter(pk=self.email5.pk).exists())

        storage = list(get_messages(self.request))
        self.assertEqual(len(storage), 2)
        self.assertEqual(f'Deleted 2 non-primary EmailAddresses.',
                         str(storage[0]))
        self.assertEqual(f'Skipped deleting 1 primary EmailAddresses.',
                         str(storage[1]))
