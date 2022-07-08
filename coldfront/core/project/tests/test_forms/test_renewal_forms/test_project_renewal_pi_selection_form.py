from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestProjectRenewalPISelectionForm(TestBase):
    """A class for testing ProjectRenewalPISelectionForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        # Create a Project for the user to renew.
        project_name = 'fc_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        self.project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        self.project_user = ProjectUser.objects.create(
            project=self.project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

    def test_eligibility_based_on_requests_in_specific_allocation_period(self):
        """Test that PI eligibility for a particular AllocationPeriod is
        only based on existing requests under the same period."""
        allocation_period = get_current_allowance_year_period()

        # Create a new project request.
        computing_allowance = self.get_fca_computing_allowance()
        new_project, new_project_request = create_project_and_request(
            'fc_new_project', 'New', computing_allowance, allocation_period,
            self.user, self.user, 'Under Review')
        self.assertNotEqual(new_project_request.status.name, 'Denied')

        # Create a renewal request.
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            computing_allowance=computing_allowance,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=self.project,
            post_project=self.project,
            request_time=utc_now_offset_aware())
        self.assertNotEqual(allocation_renewal_request.status.name, 'Denied')

        # Select a different AllocationPeriod.
        next_allowance_year_allocation_period = \
            get_next_allowance_year_period()
        self.assertIsNotNone(next_allowance_year_allocation_period)
        kwargs = {
            'computing_allowance': computing_allowance,
            'allocation_period_pk': next_allowance_year_allocation_period.pk,
            'project_pks': [self.project.pk],
        }

        # The PI should be selectable.
        form = ProjectRenewalPISelectionForm(**kwargs)
        pi_field_disabled_choices = \
            form.fields['PI'].widget.disabled_choices
        self.assertNotIn(self.project_user.pk, pi_field_disabled_choices)

        # Change the AllocationPeriods of the requests.
        new_project_request.allocation_period = \
            next_allowance_year_allocation_period
        new_project_request.save()
        allocation_renewal_request.allocation_period = \
            next_allowance_year_allocation_period
        allocation_renewal_request.save()

        # The PI should not be selectable.
        form = ProjectRenewalPISelectionForm(**kwargs)
        pi_field_disabled_choices = \
            form.fields['PI'].widget.disabled_choices
        self.assertIn(self.project_user.pk, pi_field_disabled_choices)

    def test_pis_with_non_denied_project_allocation_requests_disabled(self):
        """Test that PIs with non-'Denied'
        SavioProjectAllocationRequests are disabled in the 'PI'
        field."""
        computing_allowance = self.get_fca_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        # Create a new project request.
        new_project, new_project_request = create_project_and_request(
            'fc_new_project', 'New', computing_allowance, allocation_period,
            self.user, self.user, 'Under Review')

        # For every status except 'Denied', the PI should be disabled.
        kwargs = {
            'computing_allowance': computing_allowance,
            'allocation_period_pk': allocation_period.pk,
            'project_pks': [self.project.pk],
        }
        status_choices = ProjectAllocationRequestStatusChoice.objects.all()
        self.assertEqual(status_choices.count(), 5)
        for status_choice in status_choices:
            new_project_request.status = status_choice
            new_project_request.save()
            form = ProjectRenewalPISelectionForm(**kwargs)
            pi_field_disabled_choices = \
                form.fields['PI'].widget.disabled_choices
            if status_choice.name != 'Denied':
                self.assertIn(
                    self.project_user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(
                    self.project_user.pk, pi_field_disabled_choices)

    def test_pis_with_non_denied_allocation_renewal_requests_disabled(self):
        """Test that PIs with non-'Denied' AllocationRenewalRequests are
        disabled in the 'PI' field."""
        computing_allowance = self.get_fca_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        # Create a renewal request.
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            computing_allowance=computing_allowance,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=self.project,
            post_project=self.project,
            request_time=utc_now_offset_aware())

        # For every status except 'Denied', the PI should be disabled.
        kwargs = {
            'computing_allowance': computing_allowance,
            'allocation_period_pk': allocation_period.pk,
            'project_pks': [self.project.pk],
        }
        status_choices = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertEqual(status_choices.count(), 4)
        for status_choice in status_choices:
            allocation_renewal_request.status = status_choice
            allocation_renewal_request.save()
            form = ProjectRenewalPISelectionForm(**kwargs)
            pi_field_disabled_choices = \
                form.fields['PI'].widget.disabled_choices
            if status_choice.name != 'Denied':
                self.assertIn(
                    self.project_user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(
                    self.project_user.pk, pi_field_disabled_choices)
