from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
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

    def test_pis_with_non_denied_project_allocation_requests_disabled(self):
        """Test that PIs with non-'Denied'
        SavioProjectAllocationRequests are disabled in the 'PI'
        field."""
        # Create a Project for the user to renew.
        project_name = 'fc_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        project_user = ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        # Create a new Project.
        new_project_name = 'fc_new_project'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        # Create an 'Under Review' SavioProjectAllocationRequest for the new
        # Project.
        allocation_period = get_current_allocation_period()
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        request = SavioProjectAllocationRequest.objects.create(
            requester=self.user,
            allocation_type=SavioProjectAllocationRequest.FCA,
            allocation_period=allocation_period,
            pi=self.user,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        # For every status except 'Denied', the PI should be disabled.
        kwargs = {
            'allocation_period_pk': allocation_period.pk,
            'project_pks': [project.pk],
        }
        status_choices = ProjectAllocationRequestStatusChoice.objects.all()
        self.assertEqual(status_choices.count(), 5)
        for status_choice in status_choices:
            request.status = status_choice
            request.save()
            form = ProjectRenewalPISelectionForm(**kwargs)
            pi_field_disabled_choices = \
                form.fields['PI'].widget.disabled_choices
            if status_choice.name != 'Denied':
                self.assertIn(project_user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(project_user.pk, pi_field_disabled_choices)

    def test_pis_with_non_denied_allocation_renewal_requests_disabled(self):
        """Test that PIs with non-'Denied' AllocationRenewalRequests are
        disabled in the 'PI' field."""
        # Create a Project for the user to renew.
        project_name = 'fc_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        project_user = ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        # Create an AllocationRenewalRequest.
        allocation_period = get_current_allocation_period()
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
            'allocation_period_pk': allocation_period.pk,
            'project_pks': [project.pk],
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
                self.assertIn(project_user.pk, pi_field_disabled_choices)
            else:
                self.assertNotIn(project_user.pk, pi_field_disabled_choices)
