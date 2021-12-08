from coldfront.core.user.models import EmailAddress
from coldfront.core.user.tests.utils import TestUserBase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class TestEmailAddress(TestUserBase):
    """A class for testing the EmailAddress model."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.user = User.objects.create(
            email='user@email.com',
            first_name='First',
            last_name='Last',
            username='user')

    def test_save_nonexistent_to_primary(self):
        """Test that saving an EmailAddress as a primary one when it did
        not previously exist succeeds."""
        kwargs = {
            'user': self.user,
            'email': self.user.email,
            'is_verified': True,
            'is_primary': True,
        }
        try:
            email_address = EmailAddress.objects.create(**kwargs)
        except ValidationError:
            self.fail('A ValidationError should not have been raised.')
        self.assertTrue(email_address.is_primary)

    def test_save_non_primary_to_primary_no_others(self):
        """Test that saving an EmailAddress that was not previously
        primary as primary, when there are no other primary
        EmailAddresses, succeeds."""
        kwargs = {
            'user': self.user,
            'email': self.user.email,
            'is_verified': True,
            'is_primary': False,
        }
        try:
            email_address = EmailAddress.objects.create(**kwargs)
        except ValidationError:
            self.fail('A ValidationError should not have been raised.')
        self.assertFalse(email_address.is_primary)

        try:
            email_address.is_primary = True
            email_address.save()
        except ValidationError:
            self.fail('A ValidationError should not have been raised.')
        self.assertTrue(email_address.is_primary)

    def test_save_non_primary_to_primary_others(self):
        """Test that saving an EmailAddress that was not previously
        primary as primary, when there are other primary
        EmailAddresses, fails."""
        kwargs = {
            'user': self.user,
            'email': self.user.email,
            'is_verified': True,
            'is_primary': True,
        }
        EmailAddress.objects.create(**kwargs)

        kwargs['email'] = 'new@email.com'
        try:
            EmailAddress.objects.create(**kwargs)
        except ValidationError as e:
            self.assertIn('User already has a primary email address', str(e))
        else:
            self.fail('A ValidationError should have been raised.')

    def test_save_unverified_as_primary(self):
        """Test that saving an unverified EmailAddress as primary
        fails."""
        kwargs = {
            'user': self.user,
            'email': self.user.email,
            'is_verified': False,
            'is_primary': True,
        }
        try:
            EmailAddress.objects.create(**kwargs)
        except ValidationError as e:
            self.assertIn(
                'Only verified emails may be set to primary.', str(e))
        else:
            self.fail('A ValidationError should have been raised.')

    def test_save_updates_user_email_field_if_primary(self):
        """Test that saving a primary EmailAddress updates the "email"
        field of the User."""
        self.assertEqual(self.user.email, 'user@email.com')

        # The field should be updated if the address goes from non-primary to
        # primary.
        kwargs = {
            'user': self.user,
            'email': 'new0@email.com',
            'is_verified': True,
            'is_primary': True,
        }
        email_address = EmailAddress.objects.create(**kwargs)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, kwargs['email'])

        # The field should be updated if the address goes from primary to
        # primary.
        kwargs['email'] = 'new1@email.com'
        email_address.email = kwargs['email']
        email_address.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, kwargs['email'])
