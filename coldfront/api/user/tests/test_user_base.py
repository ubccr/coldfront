from coldfront.api.utils.tests.test_api_base import TestAPIBase
from coldfront.core.user.models import ExpiringToken
from django.contrib.auth.models import User
from django.core.management import call_command


class TestUserBase(TestAPIBase):
    """A base class for testing User-related functionality."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create default choices.
        call_command('add_default_user_choices')

        # Create a superuser.
        self.superuser = User.objects.create_superuser(
            email='superuser@nonexistent.com',
            username='superuser',
            password=self.password)

        # Fetch the staff user.
        self.staff_user = User.objects.get(username='staff')

        # Create four regular users.
        for i in range(4):
            user = User.objects.create_user(
                email=f'user{i}@nonexistent.com',
                username=f'user{i}',
                password=self.password)
            setattr(self, user.username, user)

        # Create an ExpiringToken for each User.
        for user in User.objects.all():
            token, _ = ExpiringToken.objects.get_or_create(user=user)
            setattr(self, f'{user.username}_token', token)
