from decimal import Decimal

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.utils_.new_project_user_utils import BRCNewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import LRCNewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunner
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestRunnerBase(TestBase):
    """A base class for testing NewProjectUserRunner classes."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)

        # Create a Project with a computing allowance, along with an 'Active'
        # ProjectUser.
        self.project = self.create_active_project_with_pi(
            'fc_project', self.user)
        accounting_allocation_objects = create_project_allocation(
            self.project, Decimal('0.00'))
        self.allocation = accounting_allocation_objects.allocation
        self.project_user = self.project.projectuser_set.get(user=self.user)


class TestNewProjectUserRunner(TestRunnerBase):
    """A class for testing NewProjectUserRunner."""

    def test_not_instantiatable(self):
        """Test that an instance of the class may not be
        instantiated."""
        with self.assertRaises(TypeError) as cm:
            NewProjectUserRunner(None, None)
        self.assertIn('Can\'t instantiate', str(cm.exception))


class TestBRCNewProjectUserRunner(TestRunnerBase):
    """A class for testing BRCNewProjectUserRunner."""

    pass


class TestLRCNewProjectUserRunner(TestRunnerBase):
    """A class for testing LRCNewProjectUserRunner."""

    pass


class TestNewProjectUserRunnerFactory(TestRunnerBase):
    """A class for testing NewProjectUserRunnerFactory."""

    def test_creates_expected_runner(self):
        """Test that the factory creates the expected runner, based on
        feature flags."""
        factory = NewProjectUserRunnerFactory()
        with enable_deployment('BRC'):
            runner = factory.get_runner(
                self.project_user, NewProjectUserSource.ADDED)
            self.assertIsInstance(runner, BRCNewProjectUserRunner)
        with enable_deployment('LRC'):
            runner = factory.get_runner(
                self.project_user, NewProjectUserSource.JOINED)
            self.assertIsInstance(runner, LRCNewProjectUserRunner)
