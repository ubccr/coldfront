from coldfront.core.user.models import EmailAddress
from coldfront.core.user.tests.utils import TestUserBase
from coldfront.core.user.utils import update_user_primary_email_address
from django.contrib.auth.models import User


class TestUpdateUserPrimaryEmailAddress(TestUserBase):
    """A class for testing the utility method
    update_user_primary_email_address."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.user = User.objects.create(
            email='user@email.com',
            first_name='First',
            last_name='Last',
            username='user')

    def test_creates_email_address_for_old_user_email_if_nonexistent(self):
        """Test that, if the User's email field did not have a
        corresponding EmailAddress, the method creates one that is
        verified and non-primary."""
        old_email = self.user.email
        new_primary = EmailAddress.objects.create(
            user=self.user,
            email='new@email.com',
            is_verified=True,
            is_primary=False)
        self.assertEqual(EmailAddress.objects.count(), 1)

        with self.assertLogs('', 'WARNING') as cm:
            update_user_primary_email_address(new_primary)

        self.assertEqual(EmailAddress.objects.count(), 2)
        try:
            email_address = EmailAddress.objects.get(email=old_email)
        except EmailAddress.DoesNotExist:
            self.fail(
                f'An EmailAddress for User {self.user} and email {old_email} '
                f'should have been created.')
        else:
            self.assertTrue(email_address.is_verified)
            self.assertFalse(email_address.is_primary)

        # Assert that a warning was logged.
        self.assertEqual(len(cm.output), 1)
        expected_log_message = (
            f'Created EmailAddress {email_address.pk} for User '
            f'{self.user.pk}\'s old primary address {old_email}, which '
            f'unexpectedly did not exist.')
        self.assertIn(expected_log_message, cm.output[0])

    def test_raises_type_error_for_bad_input(self):
        """Test that, if the input is not an instance of the
        EmailAddress model, a TypeError is raised."""
        bad_inputs = [None, 0, "0", self.user]
        for bad_input in bad_inputs:
            try:
                update_user_primary_email_address(bad_input)
            except TypeError as e:
                self.assertEqual(f'Invalid EmailAddress {bad_input}.', str(e))
            else:
                self.fail('A TypeError should have been raised.')

    def test_raises_value_error_for_unverified_input(self):
        """Test that, if the input is an EmailAddress with is_verified
        set to False, a ValueError is raised."""
        email_address = EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            is_verified=False,
            is_primary=False)
        try:
            update_user_primary_email_address(email_address)
        except ValueError as e:
            self.assertEqual(
                f'EmailAddress {email_address} is unverified.', str(e))
        else:
            self.fail('A ValueError should have been raised.')

    def test_sets_email_address_to_primary(self):
        """Test that the methods sets the given EmailAddress to
        primary."""
        new_primary = EmailAddress.objects.create(
            user=self.user,
            email='new@email.com',
            is_verified=True,
            is_primary=False)
        self.assertFalse(new_primary.is_primary)

        update_user_primary_email_address(new_primary)

        new_primary.refresh_from_db()
        self.assertTrue(new_primary.is_primary)

    def test_sets_user_email_field(self):
        """Test that the method sets the User's "email" field to that of
        the EmailAddress."""
        self.assertEqual(self.user.email, 'user@email.com')

        new_primary = EmailAddress.objects.create(
            user=self.user,
            email='new@email.com',
            is_verified=True,
            is_primary=False)

        update_user_primary_email_address(new_primary)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, new_primary.email)

    def test_unsets_other_primary_email_addresses(self):
        """Test that the method unsets the "is_primary" fields of other
        EmailAddresses belonging to the User."""
        kwargs = {
            'user': self.user,
            'is_verified': True,
            'is_primary': False,
        }
        for i in range(3):
            kwargs['email'] = f'{i}@email.com'
            EmailAddress.objects.create(**kwargs)
        # Bypass the "save" method, which prevents multiple primary addresses,
        # by using the "update" method.
        EmailAddress.objects.filter(user=self.user).update(is_primary=True)
        user_primary_emails = EmailAddress.objects.filter(
            user=self.user, is_primary=True)
        self.assertEqual(user_primary_emails.count(), 3)

        new_primary = EmailAddress.objects.create(
            user=self.user,
            email='new@email.com',
            is_verified=True,
            is_primary=False)

        update_user_primary_email_address(new_primary)

        user_primary_emails = EmailAddress.objects.filter(
            user=self.user, is_primary=True)
        self.assertEqual(user_primary_emails.count(), 1)
        self.assertEqual(user_primary_emails.first().pk, new_primary.pk)
