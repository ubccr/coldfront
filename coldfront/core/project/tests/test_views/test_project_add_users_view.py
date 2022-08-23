from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestProjectAddUsersViewMixin(object):
    """A mixin for testing view functionality common to both
    deployments."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@lbl.gov')
        self.pi.set_password(self.password)
        self.pi.save()
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        self.project0 = self.create_active_project_with_pi(
            'fc_project0', self.pi)
        self.allocation0 = create_project_allocation(
            self.project0, settings.ALLOCATION_MIN).allocation

    @staticmethod
    def add_users_url(project):
        """Return the URL for the view for adding users to the given
        Project."""
        return reverse('project-add-users', kwargs={'pk': project.pk})


class TestBRCProjectAddUsersView(TestProjectAddUsersViewMixin, TestBase):
    """A class for testing ProjectAddUsersView on the BRC deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

    # TODO


class TestLRCProjectAddUsersView(TestProjectAddUsersViewMixin, TestBase):
    """A class for testing ProjectAddUsersView on the LRC deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Rename the Project.
        self.project0.name = 'pc_project0'
        self.project0.save()

        # Set a billing ID for the Project.
        billing_project0 = BillingProject.objects.create(identifier='123456')
        self.billing_activity0 = BillingActivity.objects.create(
            billing_project=billing_project0, identifier='789')
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self.billing_attribute = AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=self.allocation0,
            value=str(self.billing_activity0.pk))

    def test_post_disallowed_if_project_missing_billing_activity(self):
        """Test that, if the Project does not have a default billing ID,
        POST requests are disallowed."""

        def assert_post_disallowed():
            """Assert that a POST request is disallowed."""
            self.client.login(username=self.pi, password=self.password)
            url = self.add_users_url(self.project0)
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            # An error message should be propagated to the user.
            messages = self.get_message_strings(response)
            self.assertGreater(len(messages), 0)
            message = messages[-1]
            self.assertIn('does not have a LBL Project ID', message)
            self.assertIn('cannot add users', message)

        # Set the Attribute to store an invalid BillingActivity primary key.
        self.billing_attribute.value = str(BillingActivity.objects.count() + 1)
        self.billing_attribute.save()

        assert_post_disallowed()

        # Set the Attribute to store an empty value.
        self.billing_attribute.value = '    '
        self.billing_attribute.save()

        assert_post_disallowed()

        # Delete the Attribute.
        self.billing_attribute.delete()

        assert_post_disallowed()

    # TODO
