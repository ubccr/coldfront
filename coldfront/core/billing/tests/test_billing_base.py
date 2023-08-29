from decimal import Decimal

from django.contrib.auth.models import User

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.resource.models import Resource
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.utils.email.email_strategy import DropEmailStrategy
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestBillingBase(TestBase):
    """A base class for testing Billing-related functionality."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.username = 'user'
        self.user = User.objects.create_user(
            email='user@lbl.gov', username=self.username)

        computing_allowance = Resource.objects.get(name='Recharge Allocation')
        allocation_period = get_current_allowance_year_period()
        self.project_name = 'ac_project'
        self.project, new_project_request = create_project_and_request(
            self.project_name, 'New', computing_allowance, allocation_period,
            self.user, self.user, 'Under Review')
        self.allocation = Allocation.objects.create(
            project=self.project,
            status=AllocationStatusChoice.objects.get(name='New'))
        self.allocation.resources.add(get_primary_compute_resource())

        new_project_request.billing_activity = BillingActivity.objects.create(
            billing_project=BillingProject.objects.create(identifier='000000'),
            identifier='000')
        new_project_request.save()

        runner = SavioProjectProcessingRunner(
            new_project_request, Decimal('300000.00'),
            email_strategy=DropEmailStrategy())
        runner.run()

        self.project.refresh_from_db()
        self.project_user = ProjectUser.objects.get(
            project=self.project, user=self.user)
