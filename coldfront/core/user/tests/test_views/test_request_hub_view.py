import datetime
from decimal import Decimal
from bs4 import BeautifulSoup

from django.contrib.auth.models import User
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation, get_accounting_allocation_objects
from coldfront.core.allocation.models import AllocationUserAttribute, \
    AllocationAttributeType, \
    allocation_renewal_request_state_schema, AllocationPeriod, \
    AllocationRenewalRequestStatusChoice, AllocationRenewalRequest, \
    allocation_addition_request_state_schema, \
    AllocationAdditionRequestStatusChoice, AllocationAdditionRequest
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, Project, ProjectUser, \
    ProjectUserRemovalRequestStatusChoice, ProjectUserRemovalRequest, \
    SavioProjectAllocationRequest, ProjectAllocationRequestStatusChoice, \
    savio_project_request_state_schema, vector_project_request_state_schema, \
    VectorProjectAllocationRequest, ProjectUserJoinRequest
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestRequestHubView(TestBase):
    """A class for testing RequestHubView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # self.password = 'password'

        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # create staff and admin users
        self.admin = User.objects.create(
            username='admin', email='admin@nonexistent.com', is_superuser=True)

        self.staff = User.objects.create(
            username='staff', email='staff@nonexistent.com', is_staff=True)

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        for i in range(2):
            # Create a Project and ProjectUsers.
            project = Project.objects.create(
                name=f'project{i}', status=project_status)
            setattr(self, f'project{i}', project)
            proj_user = ProjectUser.objects.create(
                user=self.user0, project=project,
                role=user_role, status=project_user_status)
            setattr(self, f'project{i}_user0', proj_user)
            pi_proj_user = ProjectUser.objects.create(
                user=self.pi, project=project, role=manager_role,
                status=project_user_status)
            setattr(self, f'project{i}_pi', pi_proj_user)

            # Create a compute allocation for the Project.
            allocation = Decimal(f'{i + 1}000.00')
            create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project.
            create_user_project_allocation(
                self.user0, project, allocation / 2)

        # set passwords
        for user in User.objects.all():
            user.set_password(self.password)
            user.save()

        self.url = reverse('request-hub')
        self.admin_url = reverse('request-hub-admin')

        self.requests = ['cluster access request',
                         'project removal request',
                         'savio project request',
                         'vector project request',
                         'project join request',
                         'project renewal request',
                         'service unit purchase request']

    def get_response(self, user, url):
        self.client.login(username=user.username, password=self.password)
        return self.client.get(url)

    def assert_no_requests(self, user, url, exclude=None):
        response = self.get_response(user, url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for request in self.requests:
            if request == exclude:
                continue
            divs = soup.find(id=f'{request.replace(" ", "_")}_section'). \
                find_all('div', {'class': 'alert alert-info'})
            self.assertEqual(len(divs), 2)
            for i, div in enumerate(divs):
                self.assertIn(request.title(), str(div))
                self.assertIn('No pending' if i == 0 else 'No completed',
                              str(div))

    def assert_pending_request_badge_shown(self, section, response, num_requests):
        soup = BeautifulSoup(response.content, 'html.parser')
        divs = soup.find(id=section)
        notification = f'{num_requests} pending request' \
                       f'{"s" if num_requests > 1 else ""}'
        self.assertIn(notification, str(divs))

    def test_access(self):
        """Testing access to RequestHubView"""

        # all users should have access to the normal view
        for user in User.objects.all():
            self.assert_has_access(self.url, user, True)

        # only staff/admin should have access to request-hub-admin
        self.assert_has_access(self.admin_url, self.admin, True)
        self.assert_has_access(self.admin_url, self.staff, True)
        self.assert_has_access(self.admin_url, self.pi, False)
        self.assert_has_access(self.admin_url, self.user0, False)
        self.assert_has_access(self.admin_url, self.user1, False)

    def test_admin_buttons(self):
        """Test that 'Go to main request page' buttons only appear for
        admin/staff"""

        def assert_button_displayed(user, displayed):
            """Assert that the relevant button appears if the
            given boolean is True; otherwise, assert that they do not
            appear."""
            button_list = [f'Go To {request.title()}s Main Page'
                           for request in self.requests]
            response = self.get_response(user, self.url)
            html = response.content.decode('utf-8')
            func = self.assertIn if displayed else self.assertNotIn

            for button in button_list:
                func(button, html)

        assert_button_displayed(self.user0, False)
        assert_button_displayed(self.admin, True)
        assert_button_displayed(self.staff, True)

    def test_no_requests(self):
        """Testing that the correct message is displayed when
        there are no requests"""

        self.assert_no_requests(self.user0, self.url)
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.pi, self.url)
        self.assert_no_requests(self.admin, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.admin_url)
        self.assert_no_requests(self.staff, self.admin_url)

    def test_cluster_access_requests(self):
        """Testing that cluster access requests appear"""

        def assert_request_shown(user, url):
            section = 'cluster_access_request_section'
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.allocation_user.user.email, pending_div)
            self.assertIn(pending_req.value, pending_div)

            # completed request is shown
            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), completed_div)
            self.assertIn(completed_req.allocation_user.user.email,
                          completed_div)
            self.assertIn(completed_req.value, completed_div)

        # creating two cluster access requests for user0
        allocation_obj = \
            get_accounting_allocation_objects(self.project0)
        allocation_user_obj = \
            get_accounting_allocation_objects(self.project0, self.user0)

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        kwargs = {
            'allocation_attribute_type': cluster_account_status,
            'allocation': allocation_obj.allocation,
            'allocation_user': allocation_user_obj.allocation_user,
        }

        pending_req = \
            AllocationUserAttribute.objects.create(value='Processing', **kwargs)

        completed_req = \
            AllocationUserAttribute.objects.create(value='Denied', **kwargs)

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='cluster access request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='cluster access request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='cluster access request')

        # should not see any requests
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.pi, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_project_removal_requests(self):
        """Testing that project removal requests appear"""
        def assert_request_shown(user, url):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'project_removal_request_section'

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.project_user.user.username, pending_div)
            self.assertIn(pending_req.requester.username, pending_div)
            self.assertIn(pending_req.request_time.strftime("%b. %d, %Y"), pending_div)
            self.assertIn(pending_req.status.name, pending_div)

            # completed request is shown
            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), pending_div)
            self.assertIn(completed_req.project_user.user.username, completed_div)
            self.assertIn(completed_req.requester.username, completed_div)
            self.assertIn(completed_req.completion_time.strftime("%b. %d, %Y"), completed_div)
            self.assertIn(completed_req.status.name, completed_div)

        processing_status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        complete_status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Complete')
        current_time = utc_now_offset_aware()

        kwargs = {
            'project_user': self.project0_user0,
            'requester': self.project0_pi.user,
            'request_time': current_time,
        }
        pending_req = ProjectUserRemovalRequest.objects.create(
            status=processing_status, **kwargs)
        completed_req = ProjectUserRemovalRequest.objects.create(
            status=complete_status,
            completion_time=current_time + datetime.timedelta(days=4),
            **kwargs
        )

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url)
        assert_request_shown(self.pi, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='project removal request')
        self.assert_no_requests(self.pi, self.url, exclude='project removal request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='project removal request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='project removal request')

        # should not see any requests
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_savio_project_requests(self):
        """Testing that savio project requests appear"""

        def assert_request_shown(user, url):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'savio_project_request_section'

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.requester.email, pending_div)
            self.assertIn(pending_req.pi.email, pending_div)
            self.assertIn(pending_req.modified.strftime("%b. %d, %Y"), pending_div)
            self.assertIn(pending_req.status.name, pending_div)

            # completed request is shown
            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), completed_div)
            self.assertIn(completed_req.requester.email, completed_div)
            self.assertIn(completed_req.pi.email, completed_div)
            self.assertIn(completed_req.modified.strftime("%b. %d, %Y"), completed_div)
            self.assertIn(completed_req.status.name, completed_div)

        kwargs = {
            'requester': self.user0,
            'allocation_type': 'FCA',
            'pi': self.pi,
            'project': self.project0,
            'pool': False,
            'survey_answers': savio_project_request_state_schema()
        }

        processing_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')
        complete_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')

        pending_req = SavioProjectAllocationRequest.objects.create(
            status=processing_status, **kwargs)
        completed_req = SavioProjectAllocationRequest.objects.create(
            status=complete_status, **kwargs)

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url)
        assert_request_shown(self.pi, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='savio project request')
        self.assert_no_requests(self.pi, self.url, exclude='savio project request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='savio project request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='savio project request')

        # should not see any requests
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_vector_project_requests(self):
        """Testing that vector project requests appear"""
        def assert_request_shown(user, url):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'vector_project_request_section'

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.requester.email, pending_div)
            self.assertIn(pending_req.pi.email, pending_div)
            self.assertIn(pending_req.modified.strftime("%b. %d, %Y"), pending_div)
            self.assertIn(pending_req.status.name, pending_div)

            # completed request is shown
            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), completed_div)
            self.assertIn(completed_req.requester.email, completed_div)
            self.assertIn(completed_req.pi.email, completed_div)
            self.assertIn(completed_req.modified.strftime("%b. %d, %Y"), completed_div)
            self.assertIn(completed_req.status.name, completed_div)

        kwargs = {
            'requester': self.user0,
            'pi': self.pi,
            'project': self.project0,
            'state': vector_project_request_state_schema()
        }

        processing_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')
        complete_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')

        pending_req = VectorProjectAllocationRequest.objects.create(
            status=processing_status, **kwargs)
        completed_req = VectorProjectAllocationRequest.objects.create(
            status=complete_status, **kwargs)

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url)
        assert_request_shown(self.pi, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='vector project request')
        self.assert_no_requests(self.pi, self.url, exclude='vector project request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='vector project request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='vector project request')

        # should not see any requests
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_project_join_requests(self):
        """Testing that project join requests appear correctly"""

        def assert_request_shown(user, url, status):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'project_join_request_section'

            # pending request is shown
            if status == 'both' or status == 'pending':
                # notification badge is shown
                self.assert_pending_request_badge_shown(
                    section, response, 1)

                pending_div = str(
                    soup.find(id=f'{section}_pending'))
                self.assertIn(pending_req.project_user.user.username, pending_div)
                self.assertIn(pending_req.project_user.project.name, pending_div)
                self.assertIn(pending_req.created.strftime("%b. %d, %Y"), pending_div)
                self.assertIn(pending_req.reason, pending_div)

            # completed request is shown
            if status == 'both' or status == 'completed':
                completed_div = str(
                    soup.find(id=f'{section}_completed'))
                self.assertIn(completed_req.project_user.user.username, completed_div)
                self.assertIn(completed_req.project_user.project.name, completed_div)
                self.assertIn(completed_req.created.strftime("%b. %d, %Y"), completed_div)
                self.assertIn(completed_req.reason, completed_div)

        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Pending - Add')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        pending_proj_user = ProjectUser.objects.create(
            user=self.user1, project=self.project0,
            role=user_role, status=project_user_status)

        pending_req = ProjectUserJoinRequest.objects.create(
            project_user=pending_proj_user,
            reason='Request hub testing.')
        completed_req = ProjectUserJoinRequest.objects.create(
            project_user=self.project0_user0,
            reason='Request hub testing.')

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url, 'completed')
        assert_request_shown(self.user1, self.url, 'pending')
        assert_request_shown(self.admin, self.admin_url, 'both')
        assert_request_shown(self.staff, self.admin_url, 'both')

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='project join request')
        self.assert_no_requests(self.user1, self.url, exclude='project join request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='project join request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='project join request')

        # should not see any requests
        self.assert_no_requests(self.pi, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_project_renewal_requests(self):
        """Testing that project renewal requests appear correctly"""

        def assert_request_shown(user, url):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'project_renewal_request_section'

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.requester.email, pending_div)
            self.assertIn(pending_req.pre_project.name, pending_div)
            self.assertIn(pending_req.post_project.name, pending_div)
            self.assertIn(pending_req.modified.strftime("%b. %d, %Y"), pending_div)
            self.assertIn(pending_req.status.name, pending_div)

            # completed request is shown
            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), completed_div)
            self.assertIn(completed_req.requester.email, completed_div)
            self.assertIn(completed_req.pre_project.name, completed_div)
            self.assertIn(completed_req.post_project.name, completed_div)
            self.assertIn(completed_req.modified.strftime("%b. %d, %Y"), completed_div)
            self.assertIn(completed_req.status.name, completed_div)
        
        kwargs = {
            'pi': self.pi,
            'requester': self.user0,
            'allocation_period': AllocationPeriod.objects.get(name='AY21-22'),
            'pre_project': self.project0,
            'post_project': self.project0,
            'num_service_units': 1000,
            'request_time': utc_now_offset_aware(),
            'state': allocation_renewal_request_state_schema()
        }
        pending_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')
        complete_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Complete')
        pending_req = AllocationRenewalRequest.objects.create(
            status=pending_status, **kwargs)
        completed_req = AllocationRenewalRequest.objects.create(
            status=complete_status, **kwargs)

        # assert the correct requests are shown
        assert_request_shown(self.user0, self.url)
        assert_request_shown(self.pi, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.user0, self.url, exclude='project renewal request')
        self.assert_no_requests(self.pi, self.url, exclude='project renewal request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='project renewal request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='project renewal request')

        # should not see any requests
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)

    def test_su_purchase_requests(self):
        """Testing that su purchase requests appear correctly"""

        def assert_request_shown(user, url):
            response = self.get_response(user, url)
            soup = BeautifulSoup(response.content, 'html.parser')
            section = 'service_unit_purchase_request_section'

            # notification badge is shown
            self.assert_pending_request_badge_shown(
                section, response, 1)

            # pending request is shown
            pending_div = str(
                soup.find(id=f'{section}_pending'))
            self.assertIn(str(pending_req.pk), pending_div)
            self.assertIn(pending_req.requester.email, pending_div)
            self.assertIn(pending_req.project.name, pending_div)
            self.assertIn(str(pending_req.num_service_units), pending_div)
            self.assertIn(pending_req.modified.strftime("%b. %d, %Y"), pending_div)
            self.assertIn(pending_req.status.name, pending_div)

            completed_div = str(
                soup.find(id=f'{section}_completed'))
            self.assertIn(str(completed_req.pk), completed_div)
            self.assertIn(completed_req.requester.email, completed_div)
            self.assertIn(completed_req.project.name, completed_div)
            self.assertIn(str(completed_req.num_service_units), completed_div)
            self.assertIn(completed_req.modified.strftime("%b. %d, %Y"), completed_div)
            self.assertIn(completed_req.status.name, completed_div)

        current_time = utc_now_offset_aware()
        kwargs = {
            'requester': self.pi,
            'project': self.project0,
            'num_service_units': 1000,
            'request_time': current_time,
            'state': allocation_addition_request_state_schema()
        }

        pending_status = AllocationAdditionRequestStatusChoice.objects.get(
            name='Under Review')
        complete_status = AllocationAdditionRequestStatusChoice.objects.get(
            name='Complete')
        pending_req = AllocationAdditionRequest.objects.create(
            status=pending_status, **kwargs)
        completed_req = AllocationAdditionRequest.objects.create(
            status=complete_status,
            completion_time=current_time + datetime.timedelta(days=4),
            **kwargs)

        # assert the correct requests are shown
        assert_request_shown(self.pi, self.url)
        assert_request_shown(self.admin, self.admin_url)
        assert_request_shown(self.staff, self.admin_url)

        # other request sections should be empty
        self.assert_no_requests(self.pi, self.url, exclude='service unit purchase request')
        self.assert_no_requests(self.admin, self.admin_url, exclude='service unit purchase request')
        self.assert_no_requests(self.staff, self.admin_url, exclude='service unit purchase request')

        # should not see any requests
        self.assert_no_requests(self.user0, self.url)
        self.assert_no_requests(self.user1, self.url)
        self.assert_no_requests(self.staff, self.url)
        self.assert_no_requests(self.admin, self.url)
