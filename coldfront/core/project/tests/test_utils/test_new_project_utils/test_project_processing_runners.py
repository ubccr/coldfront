from datetime import timedelta
from decimal import Decimal

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.tests.test_utils.test_new_project_utils.utils import TestRunnerMixinBase
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.new_project_utils import VectorProjectProcessingRunner
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestProjectProcessingRunnerMixin(TestRunnerMixinBase):
    """A mixin for testing functionality common to all runner
    classes."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.allocation = None
        # Downgrade the PI.
        self.pi.userprofile.is_pi = False
        self.pi.userprofile.save()

    def _assert_post_state(self, pre_time, post_time):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully. In particular,
        assert that the request's completion_time the given one."""
        self._refresh_objects()
        self.assertTrue(self.pi.userprofile.is_pi)
        self.assertEqual(self.project.status.name, 'Active')
        self.assertEqual(self.allocation.status.name, 'Active')
        # TODO
        self.assertEqual(self.request_obj.status.name, 'Approved - Complete')

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertFalse(self.pi.userprofile.is_pi)
        self.assertEqual(self.project.status.name, 'New')
        self.assertEqual(self.allocation.status.name, 'New')
        # TODO
        self.assertEqual(self.request_obj.status.name, 'Approved - Scheduled')

    def _create_compute_allocation(self, compute_resource):
        """Create and return an Allocation under the Project to the
        given "CLUSTER_NAME Compute" Resource."""
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(
            project=self.project, status=status)
        allocation.resources.add(compute_resource)
        return allocation

    def _create_request(self, computing_allowance, billing_activity=None):
        """Create a new project request, with the given Resource
        representing a Computing Allowance."""
        allocation_type = ComputingAllowanceInterface().name_short_from_name(
            computing_allowance.name)
        return SavioProjectAllocationRequest.objects.create(
            requester=self.requester,
            allocation_type=allocation_type,
            computing_allowance=computing_allowance,
            allocation_period=self.allocation_period,
            pi=self.pi,
            project=self.project,
            pool=False,
            survey_answers={},
            status=ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Scheduled'),
            request_time=utc_now_offset_aware() - timedelta(days=2),
            approval_time=utc_now_offset_aware() - timedelta(days=1),
            billing_activity=billing_activity)

    def _refresh_objects(self):
        """Refresh relevant objects from the database."""
        self.pi.refresh_from_db()
        self.project.refresh_from_db()
        self.allocation.refresh_from_db()
        # TODO

    def test_success(self):
        """Test that the runner performs expected processing."""
        self._assert_pre_state()

        pre_time = utc_now_offset_aware()

        with enable_deployment(self._deployment_name):
            runner = self._runner_class(*self._runner_args)
            runner.run()

        post_time = utc_now_offset_aware()

        self._assert_post_state(pre_time, post_time)


class TestBRCProjectProcessingRunner(TestProjectProcessingRunnerMixin,
                                     TestBase):
    """A class for testing SavioProjectProcessingRunner on the BRC
    deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'
        # Create a request.
        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        self.request_obj = self._create_request(computing_allowance)
        # Create an Allocation to the primary compute Resource.
        self.allocation = self._create_compute_allocation(
            get_primary_compute_resource())

        self._num_service_units = Decimal('100.00')
        self._runner_class = SavioProjectProcessingRunner
        self._runner_args = [self.request_obj, self._num_service_units]


class TestLRCProjectProcessingRunner(TestProjectProcessingRunnerMixin,
                                     TestBase):
    """A class for testing SavioProjectProcessingRunner on the LRC
    deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'LRC'
        # Set the PI's email address to be an LBL email address.
        self.pi.email = 'pi@lbl.gov'
        self.pi.save()
        # Create a BillingProject and a BillingActivity.
        self.billing_project = BillingProject.objects.create(
            identifier='123456')
        self.billing_activity = BillingActivity.objects.create(
            billing_project=self.billing_project, identifier='789')
        # Create a request.
        computing_allowance = Resource.objects.get(name=LRCAllowances.PCA)
        self.request_obj = self._create_request(
            computing_allowance, billing_activity=self.billing_activity)
        # Create an Allocation to the primary compute Resource.
        self.allocation = self._create_compute_allocation(
            get_primary_compute_resource())

        self._num_service_units = Decimal('100.00')
        self._runner_class = SavioProjectProcessingRunner
        self._runner_args = [self.request_obj, self._num_service_units]

    def _assert_post_state(self, pre_time, post_time):
        super()._assert_post_state(pre_time, post_time)

        num_billing_activities = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Billing Activity',
            allocation=self.allocation,
            value=str(self.billing_activity.pk)).count()
        self.assertEqual(num_billing_activities, 1)

        # TODO

    def _assert_pre_state(self):
        super()._assert_pre_state()

        num_billing_activities = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Billing Activity',
            allocation=self.allocation).count()
        self.assertEqual(num_billing_activities, 0)

        # TODO


class TestVectorProjectProcessingRunner(TestProjectProcessingRunnerMixin,
                                        TestBase):
    """A class for testing "VectorProjectProcessingRunner."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'
        # Rename the Project.
        self.project.name = 'vector_project'
        self.project.save()
        # Create a request.
        self.request_obj = self._create_request()
        # Create an Allocation to the 'Vector Compute' Resource.
        self.allocation = self._create_compute_allocation(
            Resource.objects.get(name='Vector Compute'))

        self._runner_class = VectorProjectProcessingRunner
        self._runner_args = [self.request_obj]

    def _create_request(self, *args, **kwargs):
        """Create a new project request."""
        return VectorProjectAllocationRequest.objects.create(
            requester=self.requester,
            pi=self.pi,
            project=self.project,
            status=ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Scheduled'))
