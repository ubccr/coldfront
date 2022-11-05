from django.contrib.auth.models import User

from coldfront.api.utils.tests.test_api_base import TestAPIBase
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.user.models import ExpiringToken


class TestBillingBase(TestAPIBase):
    """A base class for testing Billing-related functionality."""

    billing_activities_base_url = '/api/billing_activities/'

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a superuser.
        self.superuser = User.objects.create_superuser(
            email='superuser@nonexistent.com',
            username='superuser',
            password=self.password)

        # Fetch the staff user.
        self.staff_user = User.objects.get(username='staff')

        # Create a regular user.
        self.user0 = User.objects.create_user(
            email='user0@nonexistent.com',
            username='user0',
            password=self.password)

        # Create two BillingProjects, each with two BillingActivities.
        self.billing_project0 = BillingProject.objects.create(
            identifier='000000')
        self.billing_project1 = BillingProject.objects.create(
            identifier='100000')
        # 000000-000
        self.billing_activity0 = BillingActivity.objects.create(
            billing_project=self.billing_project0, identifier='000')
        # 000000-001
        self.billing_activity1 = BillingActivity.objects.create(
            billing_project=self.billing_project0, identifier='001')
        # 100000-000
        self.billing_activity2 = BillingActivity.objects.create(
            billing_project=self.billing_project1, identifier='000')
        # 100000-001
        self.billing_activity3 = BillingActivity.objects.create(
            billing_project=self.billing_project1, identifier='001')

        # Create an ExpiringToken for each User.
        for user in User.objects.all():
            token, _ = ExpiringToken.objects.get_or_create(user=user)
            setattr(self, f'{user.username}_token', token)
