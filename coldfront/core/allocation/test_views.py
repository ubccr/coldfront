import logging

from coldfront.core.project.models import Project
from coldfront.core.school.models import School
from coldfront.core.user.models import UserProfile, ApproverProfile
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import (
    UserFactory,
    ProjectFactory,
    ResourceFactory,
    AllocationFactory,
    ProjectUserFactory,
    AllocationUserFactory,
    AllocationAttributeFactory,
    ProjectStatusChoiceFactory,
    ProjectUserRoleChoiceFactory,
    AllocationStatusChoiceFactory,
    AllocationAttributeTypeFactory,
    AllocationChangeRequestFactory,
)
from coldfront.core.allocation.models import (
    AllocationChangeRequest,
    AllocationChangeStatusChoice, Allocation, AllocationStatusChoice, AllocationAttributeChangeRequest,
)

logging.disable(logging.CRITICAL)

BACKEND = "django.contrib.auth.backends.ModelBackend"

class AllocationViewBaseTest(TestCase):
    """Base class for allocation view tests."""

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        AllocationStatusChoiceFactory(name='New')
        AllocationStatusChoiceFactory(name='Pending')
        cls.project = ProjectFactory(status=ProjectStatusChoiceFactory(name='Active'))
        cls.allocation = AllocationFactory(project=cls.project)
        cls.allocation.resources.add(ResourceFactory(name='holylfs07/tier1'))
        # create allocation user that belongs to project
        allocation_user = AllocationUserFactory(allocation=cls.allocation)
        cls.allocation_user = allocation_user.user
        ProjectUserFactory(project=cls.project, user=allocation_user.user)
        # create project user that isn't an allocationuser
        proj_nonallocation_user = ProjectUserFactory()
        cls.proj_nonallocation_user = proj_nonallocation_user.user
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        manager_role = ProjectUserRoleChoiceFactory(name='Manager')
        pi_user = ProjectUserFactory(user=cls.project.pi, project=cls.project, role=manager_role)
        cls.pi_user = pi_user.user
        # make a quota TB allocation attribute
        cls.allocation_attribute = AllocationAttributeFactory(
            allocation=cls.allocation,
            value = 100,
            allocation_attribute_type=AllocationAttributeTypeFactory(name='Storage Quota (TB)'),
        )

    def allocation_access_tstbase(self, url):
        """Test basic access control for views. For all views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        utils.test_logged_out_redirect_to_login(self, url)
        utils.test_user_can_access(self, self.admin_user, url)  # admin can access


class AllocationListViewTest(AllocationViewBaseTest):
    """Tests for AllocationListView"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(AllocationListViewTest, cls).setUpTestData()
        cls.additional_allocations = [AllocationFactory() for i in list(range(100))]
        for allocation in cls.additional_allocations:
            allocation.resources.add(ResourceFactory(name='holylfs09/tier1'))
        cls.nonproj_nonallocation_user = UserFactory()

    def test_allocation_list_access_admin(self):
        """Confirm that AllocationList access control works for admin"""
        self.allocation_access_tstbase('/allocation/')
        # confirm that show_all_allocations=on enables admin to view all allocations
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['allocation_list']), 25)

    def test_allocation_list_access_pi(self):
        """Confirm that AllocationList access control works for pi
        When show_all_allocations=on, pi still sees only allocations belonging
        to the projects they are pi for.
        """
        # confirm that show_all_allocations=on enables admin to view all allocations
        self.client.force_login(self.pi_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['allocation_list']), 1)

    def test_allocation_list_access_user(self):
        """Confirm that AllocationList access control works for non-pi users
        When show_all_allocations=on, users see only the allocations they
        are AllocationUsers of.
        """
        # confirm that show_all_allocations=on is accessible to non-admin but
        # contains only the user's allocations
        self.client.force_login(self.allocation_user, backend=BACKEND)
        response = self.client.get("/allocation/")
        self.assertEqual(len(response.context['allocation_list']), 1)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['allocation_list']), 1)
        # nonallocation user belonging to project can't see allocation
        self.client.force_login(self.nonproj_nonallocation_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['allocation_list']), 0)
        # nonallocation user belonging to project can't see allocation
        self.client.force_login(self.proj_nonallocation_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['allocation_list']), 0)

    def test_allocation_list_search_admin(self):
        """Confirm that AllocationList search works for admin"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        base_url = '/allocation/?show_all_allocations=on'
        response = self.client.get(
            base_url + f'&resource_name={self.allocation.resources.first().pk}'
        )
        self.assertEqual(len(response.context['allocation_list']), 1)


class AllocationDetailViewTest(TestCase):
    """Tests for the AllocationDetailView access control."""

    def setUp(self):
        """Set up users, permissions, schools, and allocations."""
        # Create users
        self.superuser = User.objects.create(username="superuser", is_superuser=True)
        self.approver_user = User.objects.create(username="approver_user")
        self.regular_user = User.objects.create(username="regular_user")
        self.viewer_user = User.objects.create(username="viewer_user")  # Has `can_view_all_allocations`
        self.allocation_user = User.objects.create(username="allocation_user")  # Explicit allocation access

        # Create user profiles
        self.approver_profile = UserProfile.objects.get(user=self.approver_user)

        # Create schools
        self.school1 = School.objects.create(description="Tandon School of Engineering")
        self.school2 = School.objects.create(description="NYU IT")

        # Assign permissions
        self.view_all_perm = Permission.objects.get(codename="can_view_all_allocations")
        self.review_perm = Permission.objects.get(codename="can_review_allocation_requests")

        self.viewer_user.user_permissions.add(self.view_all_perm)
        self.approver_user.user_permissions.add(self.review_perm)

        # Assign schools to the approver
        self.approver_profile_obj = ApproverProfile.objects.create(user_profile=self.approver_profile)
        self.approver_profile_obj.schools.set([self.school1])  # Approver can review Tandon only

        # Create projects
        self.project1 = Project.objects.create(title="Tandon Project", school=self.school1, pi=self.approver_user)
        self.project2 = Project.objects.create(title="NYU IT Project", school=self.school2, pi=self.regular_user)

        # Create allocations
        self.allocation1 = Allocation.objects.create(
            project=self.project1, quantity=100, justification="Test allocation 1"
        )
        self.allocation2 = Allocation.objects.create(
            project=self.project2, quantity=200, justification="Test allocation 2"
        )

    def test_superuser_can_access_any_allocation(self):
        """Test that superusers can access any allocation."""
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation1.pk}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation2.pk}))
        self.assertEqual(response.status_code, 200)

    def test_user_with_can_view_all_allocations_permission_can_access(self):
        """Test that users with `can_view_all_allocations` permission can access any allocation."""
        self.client.force_login(self.viewer_user)
        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation1.pk}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation2.pk}))
        self.assertEqual(response.status_code, 200)

    def test_approver_can_access_own_school_allocation(self):
        """Test that approvers can access allocations for their assigned schools."""
        self.client.force_login(self.approver_user)
        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation1.pk}))
        self.assertEqual(response.status_code, 200)  # Approver should have access

    def test_approver_cannot_access_other_schools_allocation(self):
        """Test that approvers cannot access allocations outside their assigned schools."""
        self.client.force_login(self.approver_user)
        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation2.pk}))
        self.assertEqual(response.status_code, 403)  # Approver should NOT have access

    def test_user_with_allocation_permission_can_access(self):
        """Test that a user explicitly granted allocation access can view it."""
        # Manually grant allocation permission
        self.allocation1.grant_perm(self.allocation_user, "USER")
        self.client.force_login(self.allocation_user)

        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_access(self):
        """Test that a regular user without permissions cannot access the allocation."""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("allocation-detail", kwargs={"pk": self.allocation1.pk}))
        self.assertEqual(response.status_code, 403)


class AllocationChangeDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationChangeDetailView"""

    def setUp(self):
        """create an AllocationChangeRequest to test"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        self.alloc_change_pk = 2
        AllocationChangeRequestFactory(id=self.alloc_change_pk, allocation=self.allocation)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=self.alloc_change_pk)
        alloc_change_req_school = alloc_change_req.allocation.project.school

        # Create users
        self.superuser = UserFactory(username='superuser', is_superuser=True)
        self.approver_user = UserFactory(username='approver_user')
        self.approver_user2 = UserFactory(username='approver_user2')
        self.regular_user = UserFactory(username='regular_user')

        # Assign permissions
        self.permission = Permission.objects.get(codename="can_review_allocation_requests")
        self.approver_user.user_permissions.add(self.permission)

        # Get UserProfiles
        self.approver_profile, _ = UserProfile.objects.get_or_create(user=self.approver_user)
        self.approver_profile2, _ = UserProfile.objects.get_or_create(user=self.approver_user2)

        # Create dummy school
        self.dummy_school, _ = School.objects.get_or_create(description="Dummy School")

        # Assign permissions
        self.review_perm = Permission.objects.get(codename="can_review_allocation_requests")
        self.approver_user.user_permissions.add(self.review_perm)
        self.approver_user2.user_permissions.add(self.review_perm)

        # Assign schools to the approver
        self.approver_profile_obj = ApproverProfile.objects.create(user_profile=self.approver_profile)
        self.approver_profile_obj.schools.set([alloc_change_req_school])  # Approver can review alloc_change_req_school
        self.approver_profile_obj2 = ApproverProfile.objects.create(user_profile=self.approver_profile2)
        self.approver_profile_obj2.schools.set([self.dummy_school])  # Approver2 can review dummy school's alloc change

    def test_superuser_can_access_any_allocation_change(self):
        """Test that superusers can access any allocation change request"""
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('allocation-change-detail', kwargs={'pk': self.alloc_change_pk}))
        self.assertEqual(response.status_code, 200)

    def test_approver_can_access_own_school_allocation_change(self):
        """Test that an approver can access allocation changes related to their assigned schools"""
        self.client.force_login(self.approver_user)
        response = self.client.get(reverse('allocation-change-detail', kwargs={'pk': self.alloc_change_pk}))
        self.assertEqual(response.status_code, 200)  # Success

    def test_approver_cannot_access_other_school_allocation_change(self):
        """Test that an approver cannot access allocation changes from other schools"""
        self.client.force_login(self.approver_user2)
        response = self.client.get(reverse('allocation-change-detail', kwargs={'pk': self.alloc_change_pk}))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_regular_user_cannot_access_any_allocation_change(self):
        """Test that regular users cannot access any allocation change requests"""
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('allocation-change-detail', kwargs={'pk': self.alloc_change_pk}))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_approver_without_schools_cannot_access_allocation_change(self):
        """Test that an approver with no assigned school cannot access allocation changes"""
        self.approver_profile_obj.schools.clear()  # Remove school associations
        self.client.force_login(self.approver_user)
        response = self.client.get(reverse('allocation-change-detail', kwargs={'pk': self.alloc_change_pk}))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_allocationchangedetailview_access(self):
        response = self.client.get(
            reverse('allocation-change-detail', kwargs={'pk': 2})
        )
        self.assertEqual(response.status_code, 200)

    def test_allocationchangedetailview_post_deny(self):
        """Test that posting to AllocationChangeDetailView with action=deny
        changes the status of the AllocationChangeRequest to denied."""
        param = {'action': 'deny'}
        response = self.client.post(
            reverse('allocation-change-detail', kwargs={'pk': 2}), param, follow=True
        )
        self.assertEqual(response.status_code, 200)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        denied_status_id = AllocationChangeStatusChoice.objects.get(name='Denied').pk
        self.assertEqual(alloc_change_req.status_id, denied_status_id)


class AllocationChangeViewTest(AllocationViewBaseTest):
    """Tests for AllocationChangeView"""

    def setUp(self):
        self.client.force_login(self.admin_user, backend=BACKEND)
        self.post_data = {
            'justification': 'just a test',
            'attributeform-0-new_value': '',
            'attributeform-INITIAL_FORMS': '1',
            'attributeform-MAX_NUM_FORMS': '1',
            'attributeform-MIN_NUM_FORMS': '0',
            'attributeform-TOTAL_FORMS': '1',
            'end_date_extension': 0,
        }
        self.url = '/allocation/1/change-request'

    def test_allocationchangeview_access(self):
        """Test get request"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)  # Manager can access
        utils.test_user_cannot_access(self, self.allocation_user, self.url)  # user can't access

    def test_allocationchangeview_post_extension(self):
        """Test post request to extend end date"""

        self.post_data['end_date_extension'] = 90
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post(
            '/allocation/1/change-request', data=self.post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Allocation change request successfully submitted."
        )
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 1)

    def test_allocationchangeview_post_no_change(self):
        """Post request with no change should not go through"""

        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)

        response = self.client.post(
            '/allocation/1/change-request', data=self.post_data, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You must request a change")
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)


class AllocationDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationDetailView"""

    def setUp(self):
        self.url = f'/allocation/{self.allocation.pk}/'

    def test_allocation_detail_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)  # PI can access
        utils.test_user_cannot_access(self, self.proj_nonallocation_user, self.url)
        # check access for allocation user with "Removed" status

    def test_allocationdetail_requestchange_button(self):
        """Test visibility of "Request Change" button for different user types"""
        utils.page_contains_for_user(self, self.admin_user, self.url, 'Request Change')
        utils.page_contains_for_user(self, self.pi_user, self.url, 'Request Change')
        utils.page_does_not_contain_for_user(
            self, self.allocation_user, self.url, 'Request Change'
        )

    def test_allocationattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        # admin
        utils.page_contains_for_user(
            self, self.admin_user, self.url, 'Add Allocation Attribute'
        )
        utils.page_contains_for_user(
            self, self.admin_user, self.url, 'Delete Allocation Attribute'
        )
        # pi
        utils.page_does_not_contain_for_user(
            self, self.pi_user, self.url, 'Add Allocation Attribute'
        )
        utils.page_does_not_contain_for_user(
            self, self.pi_user, self.url, 'Delete Allocation Attribute'
        )
        # allocation user
        utils.page_does_not_contain_for_user(
            self, self.allocation_user, self.url, 'Add Allocation Attribute'
        )
        utils.page_does_not_contain_for_user(
            self, self.allocation_user, self.url, 'Delete Allocation Attribute'
        )

    def test_allocationuser_button_visibility(self):
        """Test visibility of "Add/Remove Users" buttons for different user types"""
        # admin
        utils.page_contains_for_user(self, self.admin_user, self.url, 'Add Users')
        utils.page_contains_for_user(self, self.admin_user, self.url, 'Remove Users')
        # pi
        utils.page_contains_for_user(self, self.pi_user, self.url, 'Add Users')
        utils.page_contains_for_user(self, self.pi_user, self.url, 'Remove Users')
        # allocation user
        utils.page_does_not_contain_for_user(
            self, self.allocation_user, self.url, 'Add Users'
        )
        utils.page_does_not_contain_for_user(
            self, self.allocation_user, self.url, 'Remove Users'
        )


class AllocationCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationCreateView"""

    def setUp(self):
        self.url = f'/allocation/project/{self.project.pk}/create'  # url for AllocationCreateView
        self.client.force_login(self.pi_user)
        self.post_data = {
            'justification': 'test justification',
            'quantity': '1',
            'resource': f'{self.allocation.resources.first().pk}',
        }

    def test_allocationcreateview_access(self):
        """Test access to the AllocationCreateView"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.proj_nonallocation_user, self.url)

    def test_allocationcreateview_post(self):
        """Test POST to the AllocationCreateView"""
        self.assertEqual(len(self.project.allocation_set.all()), 1)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 2)

    def test_allocationcreateview_post_zeroquantity(self):
        """Test POST to the AllocationCreateView"""
        self.post_data['quantity'] = '0'
        self.assertEqual(len(self.project.allocation_set.all()), 1)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 2)


class AllocationAddUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationAddUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.allocation.pk}/add-users'

    def test_allocationaddusersview_access(self):
        """Test access to AllocationAddUsersView"""
        self.allocation_access_tstbase(self.url)
        no_permission = 'You do not have permission to add users to the allocation.'

        self.client.force_login(self.admin_user, backend=BACKEND)
        admin_response = self.client.get(self.url)
        self.assertTrue(no_permission not in str(admin_response.content))

        self.client.force_login(self.pi_user, backend=BACKEND)
        pi_response = self.client.get(self.url)
        self.assertTrue(no_permission not in str(pi_response.content))

        self.client.force_login(self.allocation_user, backend=BACKEND)
        user_response = self.client.get(self.url)
        self.assertTrue(no_permission in str(user_response.content))


class AllocationRemoveUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationRemoveUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.allocation.pk}/remove-users'

    def test_allocationremoveusersview_access(self):
        self.allocation_access_tstbase(self.url)

class AllocationRequestListViewTest(AllocationViewBaseTest):
    """Tests for the AllocationRequestListView"""

    def setUp(self):
        self.url = '/allocation/request-list'

        # Create test users
        self.superuser = UserFactory(username='superuser', is_superuser=True)
        self.approver_user = UserFactory(username='approver_user')
        self.regular_user = UserFactory(username='regular_user')

        # Assign permissions
        permission = Permission.objects.get(codename='can_review_allocation_requests')
        self.approver_user.user_permissions.add(permission)

        # Create UserProfiles
        self.superuser_profile, _ = UserProfile.objects.get_or_create(user=self.superuser)
        self.approver_user_profile, _ = UserProfile.objects.get_or_create(user=self.approver_user)
        self.regular_profile, _ = UserProfile.objects.get_or_create(user=self.regular_user)

        # Create Schools
        self.school1, _ = School.objects.get_or_create(description="Tandon School of Engineering")
        self.school2, _ = School.objects.get_or_create(description="NYU IT")

        # Set Approver Profile
        self.approver_profile, _ = ApproverProfile.objects.get_or_create(user_profile=self.approver_user_profile)
        self.approver_profile.schools.set([self.school1])

        # Create Projects
        status = ProjectStatusChoiceFactory(name='Active')
        self.project1 = Project.objects.create(title="Tandon School of Engineering Project 1", school=self.school1,
                                               pi=self.approver_user_profile.user, status=status)
        self.project2 = Project.objects.create(title="NYU IT Project 2", school=self.school2, pi=self.regular_profile.user,
                                               status=status)

        # Create Allocations
        self.allocation1 = Allocation.objects.create(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name="New"),
            quantity=100,
            start_date="2025-01-01",
            end_date="2025-12-31",
            justification="Testing allocation 1",
        )
        self.allocation2 = Allocation.objects.create(
            project=self.project2,
            status=AllocationStatusChoice.objects.get(name="New"),
            quantity=200,
            start_date="2025-02-01",
            end_date="2025-12-31",
            justification="Testing allocation 2",
        )

    # TODO: check why login_url = '/' was set in AllocationRequestListView
    # def test_allocationrequestlistview_access(self):
    #     """Test that the allocation request list view is accessible for permitted users."""
    #     self.allocation_access_tstbase(self.url)

    def test_superuser_can_see_all_allocation_requests(self):
        """Test that superusers can see all allocation requests."""
        self.client.force_login(self.superuser, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.allocation1.project.school.description)
        self.assertContains(response, self.allocation2.project.school.description)

    def test_approver_can_only_see_own_school_allocations(self):
        """Test that approvers can only see allocation requests for their assigned schools."""
        self.client.force_login(self.approver_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.allocation1.project.school.description)
        self.assertNotContains(response, self.allocation2.project.school.description)

    def test_non_approver_cannot_access_page(self):
        """Test that a regular user without the `can_review_allocation_requests` permission cannot access."""
        self.client.force_login(self.regular_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)  # Expect Forbidden access

    def test_approver_with_no_school_sees_empty_list(self):
        """Test that an approver without an assigned school sees an empty list."""
        self.approver_profile.schools.clear()
        self.client.force_login(self.approver_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.allocation1.project.school.description)
        self.assertNotContains(response, self.allocation2.project.school.description)
        self.assertContains(response, "You are not associated with any school.")


class AllocationChangeListViewTest(AllocationViewBaseTest):
    """Tests for the AllocationChangeListView"""

    def setUp(self):
        self.url = '/allocation/change-list'

        # Create test users
        self.superuser = UserFactory(username='superuser', is_superuser=True)
        self.approver_user = UserFactory(username='approver_user')
        self.regular_user = UserFactory(username='regular_user')

        # Assign permissions
        permission = Permission.objects.get(codename='can_review_allocation_requests')
        self.approver_user.user_permissions.add(permission)

        # Create UserProfiles
        self.superuser_profile, _ = UserProfile.objects.get_or_create(user=self.superuser)
        self.approver_user_profile, _ = UserProfile.objects.get_or_create(user=self.approver_user)
        self.regular_profile, _ = UserProfile.objects.get_or_create(user=self.regular_user)
        # Create Schools
        self.school1, _ = School.objects.get_or_create(description="Tandon School of Engineering")
        self.school2, _ = School.objects.get_or_create(description="NYU IT")
        # Set Approver Profile
        self.approver_profile, _ = ApproverProfile.objects.get_or_create(user_profile=self.approver_user_profile)
        self.approver_profile.schools.set([self.school1])

        # Create Projects
        status = ProjectStatusChoiceFactory(name='Active')
        self.project1 = Project.objects.create(title="Tandon School of Engineering Project 1", school=self.school1,
                                               pi=self.approver_user_profile.user, status=status)
        self.project2 = Project.objects.create(title="NYU IT Project 2", school=self.school2, pi=self.regular_profile.user,
                                               status=status)

        # Create Allocations
        self.allocation1 = Allocation.objects.create(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name="Pending"),
            quantity=100,
            start_date="2025-01-01",
            end_date="2025-12-31",
            justification="Testing allocation 1",
        )
        self.allocation2 = Allocation.objects.create(
            project=self.project2,
            status=AllocationStatusChoice.objects.get(name="Pending"),
            quantity=200,
            start_date="2025-02-01",
            end_date="2025-12-31",
            justification="Testing allocation 2",
        )

        # Create AllocationChangeStatusChoice
        self.pending_status, _ = AllocationChangeStatusChoice.objects.get_or_create(name="Pending")

        # Create AllocationChangeRequest
        self.allocation_change1 = AllocationChangeRequest.objects.create(
            allocation=self.allocation1,
            status=self.pending_status,
            end_date_extension=30,
            justification="Need to extend allocation 1",
            notes="Request submitted for review"
        )
        self.allocation_change2 = AllocationChangeRequest.objects.create(
            allocation=self.allocation2,
            status=self.pending_status,
            end_date_extension=60,
            justification="Need to extend allocation 2",
            notes="Urgent request"
        )

    def test_allocationchangelistview_access(self):
        self.allocation_access_tstbase(self.url)

    def test_superuser_can_see_all_allocation_changes(self):
        """Test that superusers can see all allocation change requests."""
        self.client.force_login(self.superuser, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.allocation1.project.school.description)
        self.assertContains(response, self.allocation2.project.school.description)

    def test_approver_can_only_see_own_school_allocations(self):
        """Test that approvers can only see allocation changes for their assigned schools."""
        self.client.force_login(self.approver_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.allocation_change1.allocation.project.school.description)
        self.assertNotContains(response, self.allocation_change2.allocation.project.school.description)

    def test_non_approver_cannot_access_page(self):
        """Test that a regular user without the `can_review_allocation_requests` permission cannot access."""
        self.client.force_login(self.regular_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)  # Expect Forbidden access

    def test_approver_with_no_school_sees_empty_list(self):
        """Test that an approver without an assigned school sees an empty list."""
        self.approver_profile.schools.clear()
        self.client.force_login(self.approver_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.allocation_change1.allocation.project.school.description)
        self.assertNotContains(response, self.allocation_change2.allocation.project.school.description)
        self.assertContains(response, "You are not associated with any school.")


class AllocationNoteCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationNoteCreateView"""

    def setUp(self):
        self.url = f'/allocation/{self.allocation.pk}/allocationnote/add'

    def test_allocationnotecreateview_access(self):
        self.allocation_access_tstbase(self.url)

class AllocationChangeDeleteAttributeViewTest(AllocationViewBaseTest):
    """Tests for the AllocationChangeDeleteAttributeView"""

    def setUp(self):
        # Create test users
        self.superuser = UserFactory(username='superuser', is_superuser=True)
        self.approver_user = UserFactory(username='approver_user')
        self.regular_user = UserFactory(username='regular_user')

        # Assign permissions
        permission = Permission.objects.get(codename='can_review_allocation_requests')
        self.approver_user.user_permissions.add(permission)
        self.approver_user.save()

        # Create UserProfiles
        self.superuser_profile, _ = UserProfile.objects.get_or_create(user=self.superuser)
        self.approver_user_profile, _ = UserProfile.objects.get_or_create(user=self.approver_user)
        self.regular_profile, _ = UserProfile.objects.get_or_create(user=self.regular_user)

        # Create Schools
        self.school1, _ = School.objects.get_or_create(description="Tandon School of Engineering")
        self.school2, _ = School.objects.get_or_create(description="NYU IT")

        # Set Approver Profile
        self.approver_profile, _ = ApproverProfile.objects.get_or_create(user_profile=self.approver_user_profile)
        self.approver_profile.schools.set([self.school1])

        # Create Projects
        status = ProjectStatusChoiceFactory(name='Active')
        self.project1 = Project.objects.create(title="Tandon Engineering Project", school=self.school1,
                                               pi=self.approver_user_profile.user, status=status)
        self.project2 = Project.objects.create(title="NYU IT Project", school=self.school2,
                                               pi=self.regular_profile.user, status=status)

        # Create Allocations
        self.allocation1 = Allocation.objects.create(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name="New"),
            quantity=100,
            start_date="2025-01-01",
            end_date="2025-12-31",
            justification="Testing allocation 1",
        )
        self.allocation2 = Allocation.objects.create(
            project=self.project2,
            status=AllocationStatusChoice.objects.get(name="New"),
            quantity=200,
            start_date="2025-02-01",
            end_date="2025-12-31",
            justification="Testing allocation 2",
        )
        pending_status, _ = AllocationChangeStatusChoice.objects.get_or_create(name="Pending")
        # Create AllocationChangeRequests
        self.allocation_change1 = AllocationChangeRequest.objects.create(
            allocation=self.allocation1,
            status=pending_status,
            end_date_extension=30,
            justification="Extend allocation 1",
            notes="Pending review"
        )
        self.allocation_change2 = AllocationChangeRequest.objects.create(
            allocation=self.allocation2,
            status=pending_status,
            end_date_extension=60,
            justification="Extend allocation 2",
            notes="Urgent request"
        )

        # Create AllocationAttributeChangeRequests
        self.attribute_change1 = AllocationAttributeChangeRequest.objects.create(
            allocation_change_request=self.allocation_change1,
            allocation_attribute = self.allocation_attribute
        )
        self.attribute_change2 = AllocationAttributeChangeRequest.objects.create(
            allocation_change_request=self.allocation_change2,
            allocation_attribute = self.allocation_attribute
        )

    def test_superuser_can_delete_any_attribute_change_request(self):
        """Test that a superuser can delete any allocation attribute change request."""
        url = reverse('allocation-attribute-change-delete', kwargs={'pk': self.attribute_change1.pk})
        self.client.force_login(self.superuser, backend=BACKEND)
        response = self.client.get(url)
        self.assertRedirects(response, reverse('allocation-change-detail', kwargs={'pk': self.allocation_change1.pk}))
        self.assertFalse(AllocationAttributeChangeRequest.objects.filter(pk=self.attribute_change1.pk).exists())

    def test_approver_can_delete_own_school_attribute_change_request(self):
        """Test that an approver can delete an allocation attribute change request for their assigned school."""
        url = reverse('allocation-attribute-change-delete', kwargs={'pk': self.attribute_change1.pk})
        self.client.force_login(self.approver_user)
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('allocation-change-detail', kwargs={'pk': self.allocation_change1.pk}))
        self.assertFalse(AllocationAttributeChangeRequest.objects.filter(pk=self.attribute_change1.pk).exists())

    def test_approver_cannot_delete_other_school_attribute_change_request(self):
        """Test that an approver cannot delete an allocation attribute change request outside their assigned school."""
        url = reverse('allocation-attribute-change-delete', kwargs={'pk': self.attribute_change2.pk})
        self.client.force_login(self.approver_user, backend=BACKEND)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Expect 403 Forbidden
        self.assertTrue(AllocationAttributeChangeRequest.objects.filter(pk=self.attribute_change2.pk).exists())

    def test_regular_user_cannot_access_delete_attribute_change_page(self):
        """Test that a regular user cannot delete any allocation attribute change request."""
        self.client.force_login(self.regular_user, backend=BACKEND)
        url = reverse('allocation-attribute-change-delete', kwargs={'pk': self.attribute_change1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Expect Forbidden access

    def test_approver_without_school_cannot_delete_any_request(self):
        """Test that an approver without an assigned school cannot delete an allocation attribute change request."""
        self.approver_profile.schools.clear()  # Remove assigned schools
        self.client.force_login(self.approver_user, backend=BACKEND)
        url = reverse('allocation-attribute-change-delete', kwargs={'pk': self.attribute_change1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Expect 403 Forbidden
        # Ensure the allocation attribute change request still exists
        self.assertTrue(AllocationAttributeChangeRequest.objects.filter(pk=self.attribute_change1.pk).exists())
