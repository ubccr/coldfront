from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExistingPIForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.tests.utils import create_fca_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestSavioProjectExistingPIForm(TestBase):
    """A class for testing SavioProjectExistingPIForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def test_eligibility_based_on_requests_in_specific_allocation_period(self):
        """Test that PI eligibility for a particular AllocationPeriod is
        only based on existing requests under the same period."""
        allocation_period = get_current_allowance_year_period()

        # Create a new project request.
        new_project, new_project_request = create_fca_project_and_request(
            'fc_new_project', 'Denied', allocation_period, self.user,
            self.user, 'Under Review')

        # Create a Project for the user to renew.
        project_name = 'fc_project'
        # Use 'Denied' for testing since another check disables PIs with
        # Projects having the other statuses.
        denied_project_status = ProjectStatusChoice.objects.get(name='Denied')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=denied_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        # Create an AllocationRenewalRequest.
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())

        # Select a different AllocationPeriod.
        next_allowance_year_allocation_period = \
            AllocationPeriod.objects.filter(
                name__startswith='Allowance Year',
                start_date__gt=display_time_zone_current_date()).first()
        self.assertIsNotNone(next_allowance_year_allocation_period)
        kwargs = {
            'allocation_type': 'FCA',
            'allocation_period': next_allowance_year_allocation_period,
        }

        # The PI should be selectable.
        form = SavioProjectExistingPIForm(**kwargs)
        pi_field_disabled_choices = \
            form.fields['PI'].widget.disabled_choices
        self.assertNotIn(self.user.pk, pi_field_disabled_choices)

        # Change the AllocationPeriods of the requests.
        new_project_request.allocation_period = \
            next_allowance_year_allocation_period
        new_project_request.save()
        allocation_renewal_request.allocation_period = \
            next_allowance_year_allocation_period
        allocation_renewal_request.save()

        # The PI should not be selectable.
        form = SavioProjectExistingPIForm(**kwargs)
        pi_field_disabled_choices = \
            form.fields['PI'].widget.disabled_choices
        self.assertIn(self.user.pk, pi_field_disabled_choices)

    def test_pis_with_inactive_fc_projects_disabled(self):
        """Test that PIs of Projects with the 'Inactive' status are
        disabled in the 'PI' field."""
        inactive_name = 'fc_inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        inactive_project = Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        # Add the user as a PI on both Projects.
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        kwargs = {
            'project': inactive_project,
            'role': pi_role,
            'status': active_status,
            'user': self.user,
        }
        ProjectUser.objects.create(**kwargs)

        form = SavioProjectExistingPIForm(allocation_type='FCA')
        pi_field_disabled_choices = form.fields['PI'].widget.disabled_choices
        self.assertIn(self.user.pk, pi_field_disabled_choices)

    def test_pis_with_non_denied_project_allocation_requests_disabled(self):
        """Test that PIs with non-'Denied'
        SavioProjectAllocationRequests are disabled in the 'PI'
        field."""
        allocation_period = get_current_allowance_year_period()
        # Create a new project request.
        new_project, new_project_request = create_fca_project_and_request(
            'fc_new_project', 'Denied', allocation_period, self.user,
            self.user, 'Under Review')

        # For every status except 'Denied', the PI should be disabled.
        kwargs = {
            'allocation_type': 'FCA',
            'allocation_period': allocation_period,
        }
        status_choices = ProjectAllocationRequestStatusChoice.objects.all()
        self.assertEqual(status_choices.count(), 5)
        for status_choice in status_choices:
            new_project_request.status = status_choice
            new_project_request.save()
            form = SavioProjectExistingPIForm(**kwargs)
            pi_field_disabled_choices = \
                form.fields['PI'].widget.disabled_choices
            if status_choice.name != 'Denied':
                self.assertIn(self.user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(self.user.pk, pi_field_disabled_choices)

    def test_pis_with_non_denied_allocation_renewal_requests_disabled(self):
        """Test that PIs with non-'Denied' AllocationRenewalRequests
        are disabled in the 'PI' field."""
        # Create a Project for the user to renew.
        project_name = 'fc_project'
        # Use 'Denied' for testing since another check disables PIs with
        # Projects having the other statuses.
        denied_project_status = ProjectStatusChoice.objects.get(name='Denied')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=denied_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        allocation_period = get_current_allowance_year_period()
        # Create an AllocationRenewalRequest.
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())

        # For every status except 'Denied', the PI should be disabled.
        kwargs = {
            'allocation_type': 'FCA',
            'allocation_period': allocation_period,
        }
        status_choices = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertEqual(status_choices.count(), 4)
        for status_choice in status_choices:
            allocation_renewal_request.status = status_choice
            allocation_renewal_request.save()
            form = SavioProjectExistingPIForm(**kwargs)

            pi_field_disabled_choices = \
                form.fields['PI'].widget.disabled_choices
            if status_choice.name != 'Denied':
                self.assertIn(self.user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(self.user.pk, pi_field_disabled_choices)

    # TODO: Test LRC-only functionality. PIs are only shown/allowed if
    #  they have an lbl.gov email
