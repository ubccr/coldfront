import logging

from django.db.models import Count
from django.test import TestCase
from django.urls import reverse

from coldfront.core.test_helpers import utils
from coldfront.core.allocation.models import (
    Allocation,
    AllocationUserNote,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationChangeRequest,
)
from coldfront.core.resource.models import Resource
from coldfront.core.test_helpers.factories import (
    setup_models,
    UserFactory,
    ResourceFactory,
    ResourceTypeFactory,
    AllocationFactory,
    AllocationChangeRequestFactory,
)


logging.disable(logging.CRITICAL)

UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

BACKEND = "django.contrib.auth.backends.ModelBackend"


class AllocationQC(TestCase):
    def check_resource_quotas(self):
        zero_quotas = AllocationAttribute.objects.filter(
            allocation_attribute_type__in=[1, 5], value=0
        )
        self.assertEqual(zero_quotas.count(), 0)

    def check_resource_counts(self):
        over_one = Allocation.objects.annotate(
            resource_count=Count('resources')
        ).filter(resource_count__gt=1)
        self.assertEqual(over_one.count(), 0)


class AllocationViewBaseTest(TestCase):
    """Base class for allocation view tests."""

    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        setup_models(cls)

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
        cls.additional_allocations = [
            AllocationFactory() for i in list(range(50))
        ]
        for allocation in cls.additional_allocations:
            allocation.resources.add(Resource.objects.get(name='holylfs09/tier1'))
        cls.nonproj_nonallocationuser = UserFactory(username='rdrake')

    def test_allocation_list_access_admin(self):
        """Confirm that AllocationList access control works for admin"""
        self.allocation_access_tstbase('/allocation/')
        # confirm that show_all_allocations=on enables admin to view all allocations
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), Allocation.objects.all().count())

    def test_allocation_list_access_pi(self):
        """Confirm that AllocationList access control works for pi
        When show_all_allocations=on, pi still sees only allocations belonging
        to the projects they are pi for.
        PI sees all Allocations belonging to their Project, even if they're not
        AllocationUsers
        """
        self.client.force_login(self.pi_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 2)
        # PI is not an allocationuser in either allocation but can still see them
        for allocation in response.context['item_list']:
            allocation_user_exists = allocation.allocationuser_set.filter(
                user=self.pi_user
            ).exists()
            self.assertFalse(allocation_user_exists, 
                            "User should not be connected to this allocation")

    def test_allocation_list_access_manager(self):
        """Confirm that AllocationList access control works for managers
        When show_all_allocations=on, manager still sees only allocations belonging
        to the projects they are manager for.
        Managers see all Project Allocations even if not AllocationUsers.
        """
        # confirm that show_all_allocations=on enables admin to view all allocations
        self.client.force_login(self.proj_datamanager, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 2)
        # confirm that show_all_allocations=on enables admin to view all allocations
        self.client.force_login(self.proj_accessmanager, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 2)
        for allocation in response.context['item_list']:
            allocation_user_exists = allocation.allocationuser_set.filter(
                user__in=[self.proj_datamanager, self.proj_accessmanager]
            ).exists()
            self.assertFalse(allocation_user_exists, 
                            "User should not be connected to this allocation")

    def test_allocation_list_access_proj_allocationuser(self):
        """Confirm that AllocationList access control works for non-pi users
        When show_all_allocations=on, users see only the allocations they
        are AllocationUsers of.
        """
        # confirm that show_all_allocations=on is accessible to non-admin but
        # contains only the user's allocations
        self.client.force_login(self.proj_allocationuser, backend=BACKEND)
        response = self.client.get("/allocation/")
        self.assertEqual(len(response.context['item_list']), 2)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 2)

    def test_allocation_list_access_nonproj_allocationuser(self):
        """non-ProjectUser AllocationUser can see all Allocations they belong to
        """
        self.client.force_login(self.nonproj_allocationuser, backend=BACKEND)
        response = self.client.get("/allocation/")
        self.assertEqual(len(response.context['item_list']), 2)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 2)

    def test_allocation_list_access_proj_nonallocationuser(self):
        """
        non-AllocationUser ProjectUser can see storage but not cluster Allocations
        """
        self.client.force_login(self.proj_nonallocationuser, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 1)
        # confirm that resource_type of allocation is Storage
        self.assertEqual(
            response.context['item_list'][0].resources.first().resource_type.name, 'Storage')

    def test_allocation_list_access_nonproj_nonallocationuser(self):
        """non-ProjectUser non-AllocationUser User can see no Allocations
        """
        # nonallocation user not belonging to project can't see allocation
        self.client.force_login(self.nonproj_nonallocationuser, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context['item_list']), 0)

    def test_allocation_list_search_admin(self):
        """Confirm that AllocationList search works for admin"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        base_url = '/allocation/?show_all_allocations=on'
        response = self.client.get(
            base_url + f'&resource_name={self.storage_allocation.resources.first().pk}'
        )
        self.assertEqual(len(response.context['item_list']), 1)


class AllocationChangeDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationChangeDetailView"""

    def setUp(self):
        """create an AllocationChangeRequest to test"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        AllocationChangeRequestFactory(id=2, allocation=self.storage_allocation)
        self.url = reverse('allocation-change-detail', kwargs={'pk': 2})

    def test_allocationchangedetailview_access(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_allocationchangedetailview_post_permissions_admin(self):
        """Test post request"""
        param = {'action': 'deny'}
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.post(self.url, param, follow=True)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        self.assertEqual(alloc_change_req.status_id, 3)

    def test_allocationchangedetailview_post_permissions_pi(self):
        """pi can't post changes"""
        param = {'action': 'deny'}
        self.client.force_login(self.pi_user, backend=BACKEND)
        self.client.post(self.url, param, follow=True)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        self.assertNotEqual(alloc_change_req.status_id, 3)

    def test_allocationchangedetailview_post_permissions_normaluser(self):
        """normal user can't post changes"""
        param = {'action': 'deny'}
        self.client.force_login(self.proj_allocationuser, backend=BACKEND)
        self.client.post(self.url, param, follow=True)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        self.assertNotEqual(alloc_change_req.status_id, 3)

    def test_allocationchangedetailview_post_deny(self):
        param = {'action': 'deny'}
        response = self.client.post(self.url, param, follow=True)
        self.assertEqual(response.status_code, 200)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        self.assertEqual(alloc_change_req.status_id, 3)

    def test_allocationchangedetailview_post_approve(self):
        # with nothing changed, should get error message of "You must make a change to the allocation."
        param = {'action': 'approve'}
        response = self.client.post(self.url, param, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(str(messages[0]), "You must make a change to the allocation.")


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
        self.success_msg = "Allocation change request successfully submitted."

    def test_allocationchangeview_access(self):
        """Test get request"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)  # Manager can access
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.url)  # user can't access

    def test_allocationchangeview_post_permissions(self):
        """Test post request"""
        self.post_data['attributeform-0-new_value'] = '1000'
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.post(self.url, data=self.post_data, follow=True)

        self.assertContains(response, self.success_msg)
        self.client.force_login(self.pi_user, backend=BACKEND)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, self.success_msg)

        self.client.force_login(self.proj_allocationuser, backend=BACKEND)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_allocationchangeview_post_extension(self):
        """Test post request to extend end date"""
        self.post_data['end_date_extension'] = 90
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.success_msg)
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 1)

    def test_allocationchangeview_post_no_change(self):
        """Post request with no change should not go through"""
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "You must request a change")
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)

    def test_allocationchangeview_post_more_tb(self):
        """Post request with more TB should go through"""
        self.post_data['attributeform-0-new_value'] = '1000'
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, self.success_msg)
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 1)

    def test_allocationchangeview_post_more_tb_decimal(self):
        """Post request for more TB with decimal should not go through"""
        self.post_data['attributeform-0-new_value'] = '1000.1'
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "Value must be an integer.")
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)


class AllocationDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationDetailView"""

    def setUp(self):
        self.url = f'/allocation/{self.storage_allocation.pk}/'

    def test_allocation_detail_access(self):
        self.allocation_access_tstbase(self.url)
        # pi, project nonallocation user, nonproj_allocationuser can access
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.proj_nonallocationuser, self.url)
        utils.test_user_can_access(self, self.nonproj_allocationuser, self.url)
        # check access for allocation user with "Removed" status

    def test_allocation_detail_template_value_render(self):
        """Confirm that quota_tb and usage_tb are correctly rendered in the
        generated AllocationDetailView
        """
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # check that allocation.size_exact has value
        self.assertEqual(response.context['allocation'].size_exact, 109951162777600)
        # check that allocation.usage_exact has value
        self.assertEqual(response.context['allocation'].usage_exact, 10995116277760)

    def test_allocationdetail_requestchange_button(self):
        """Test visibility of "Request Change" button for different user types"""
        search_text = 'Request Change'
        utils.page_contains_for_user(self, self.admin_user, self.url, search_text)
        utils.page_contains_for_user(self, self.pi_user, self.url, search_text)
        utils.page_contains_for_user(self, self.proj_datamanager, self.url, search_text)
        utils.page_does_not_contain_for_user(
            self, self.proj_accessmanager, self.url, search_text)
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, search_text)

    def test_allocationattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        # admin
        add_text = 'Add Allocation Attribute'
        delete_text = 'Delete Allocation Attribute'
        utils.page_contains_for_user(self, self.admin_user, self.url, add_text)
        utils.page_contains_for_user(self, self.admin_user, self.url, delete_text)
        # pi
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, add_text)
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, delete_text)
        # allocation user
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, add_text
        )
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, delete_text
        )

    def test_storage_allocationuser_button_visibility(self):
        """Test visibility of "Add/Remove Users" buttons for different user types"""
        # these buttons will only be available for compute allocations
        # admin can't see add/remove users buttons
        utils.page_does_not_contain_for_user(
            self, self.admin_user, self.url, 'Add Users'
        )
        utils.page_does_not_contain_for_user(
            self, self.admin_user, self.url, 'Remove Users'
        )
        # pi can't see add/remove users buttons
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, 'Add Users')
        utils.page_does_not_contain_for_user(
            self, self.pi_user, self.url, 'Remove Users'
        )
        # allocation user can't see add/remove users buttons
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, 'Add Users'
        )
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, 'Remove Users'
        )


class AllocationDetailViewPostTest(AllocationViewBaseTest):
    def setUp(self):
        self.new_allocation = AllocationFactory(
            project=self.project, quantity=20, justification='test new allocation',
            status=AllocationStatusChoice.objects.get(name='New')
        )
        self.new_allocation.resources.add(Resource.objects.get(name='holylfs09/tier1'))
        quotatb = AllocationAttributeType.objects.get(name='Storage Quota (TB)')
        self.new_allocation.allocationattribute_set.create(
            value=20, allocation_attribute_type=quotatb
        )
        self.url = f'/allocation/{self.new_allocation.pk}/'

    def test_allocationdetail_approval_post(self):
        """test approval of new allocation"""
        self.client.force_login(self.admin_user)
        form_data = {
            'status': AllocationStatusChoice.objects.get(name='Active').pk,
            #'start_date': self.new_allocation.start_date,
            #'end_date': self.new_allocation.end_date,
            'description': "description test",
            'is_locked': False,
            'is_changeable': True,
            'resource': self.new_allocation.resources.first().pk,
            'action': 'approve',
            'auto_create_opts': '1',
        }
        response = self.client.post(self.url, data=form_data, follow=True)
        # confirm that messages in response contains "Allocation Activated"
        self.assertContains(response, 'Allocation Activated')
        self.new_allocation.refresh_from_db()
        self.assertEqual(self.new_allocation.status.name, 'Active')


class AllocationCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationCreateView"""

    def setUp(self):
        self.url = f'/allocation/project/{self.project.pk}/create' # url for AllocationCreateView
        self.client.force_login(self.pi_user)
        tier_restype = ResourceTypeFactory(name='Storage Tier')
        storage_tier = ResourceFactory(resource_type=tier_restype)
        self.post_data = {
            'justification': 'test justification',
            'quantity': '1',
            'expense_code': '123-12312-3123-123123-123123-1231-23123',
            'tier': f'{storage_tier.pk}',
        }

    def test_allocationcreateview_access(self):
        """Test access to the AllocationCreateView"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.proj_datamanager, self.url)
        utils.test_user_cannot_access(self, self.proj_accessmanager, self.url)
        utils.test_user_cannot_access(self, self.proj_nonallocationuser, self.url)

    def test_allocationcreateview_post(self):
        """Test POST to the AllocationCreateView"""
        self.assertEqual(len(self.project.allocation_set.all()), 2)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 3)

    def test_allocationcreateview_post_zeroquantity(self):
        """Test POST to the AllocationCreateView with default post_data:
        No expense_code, dua, heavy_io, mounted, external_sharing, high_security
        """
        self.post_data['quantity'] = '0'
        self.assertEqual(len(self.project.allocation_set.all()), 2)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 3)

    def test_allocationcreateview_post_offerlettercode_valid(self):
        """ensure 33-digit codes go through and get formatted"""
        # correct # of digits with no dashes
        aa_objs = AllocationAttribute.objects.all()
        aa_obj = aa_objs.filter(allocation_attribute_type__name='Expense Code')
        self.assertEqual(len(aa_obj), 0)
        self.post_data['expense_code'] = '123' * 11
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "Allocation requested.")
        aa_obj = aa_objs.filter(allocation_attribute_type__name='Expense Code')
        self.assertEqual(len(aa_obj), 1)

    def test_allocationcreateview_post_bools(self):
        """ensure booleans are properly saved"""
        aa_names = ['Heavy IO', 'Mounted', 'High Security', 'DUA', 'External Sharing']
        self.post_data['additional_specifications'] = aa_names
        response = self.client.post(self.url, data=self.post_data, follow=True)
        aa_objs = AllocationAttribute.objects.filter(
            allocation_attribute_type__name__in=aa_names
        )
        self.assertEqual(len(aa_objs), 5)

    def test_allocationcreateview_post_offerlettercode_multiplefield_invalid(self):
        """Ensure that form won't pass if multiple expense codes are given"""
        self.post_data['existing_expense_codes'] = '000-000-000-000-000-000-000-000-000-000-000'
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "must either select an existing expense code or")

    def test_allocationcreateview_post_hsph_offerlettercode(self):
        """Ensure that form goes through if existing_expense_codes is checked"""
        self.post_data['existing_expense_codes'] = '000-000-000-000-000-000-000-000-000-000-000'
        self.post_data.pop('expense_code')
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, "Allocation requested.")

        aa_obj = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Expense Code'
        )
        self.assertEqual(len(aa_obj), 1)
        self.assertEqual(aa_obj[0].value, '000-00000-0000-000000-000000-0000-00000')


class AllocationAddUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationAddUsersView"""

    def setUp(self):
        self.compute_url = f'/allocation/{self.cluster_allocation.pk}/add-users'

    def test_allocationaddusersview_access(self):
        self.allocation_access_tstbase(self.compute_url)
        utils.test_user_can_access(self, self.pi_user, self.compute_url)
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.compute_url)


class AllocationRemoveUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationRemoveUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.storage_allocation.pk}/remove-users'

    def test_allocationremoveusersview_access(self):
        """No storage allocations have this view available"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

class AllocationRequestListViewTest(AllocationViewBaseTest):
    """Tests for the AllocationRequestListView"""

    def setUp(self):
        self.url = '/allocation/request-list'

    def test_allocationrequestlistview_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)


class AllocationChangeListViewTest(AllocationViewBaseTest):
    """Tests for the AllocationChangeListView"""

    def setUp(self):
        self.url = '/allocation/change-list'

    def test_allocationchangelistview_access(self):
        self.allocation_access_tstbase(self.url)

    def test_allocationchangelistview_changetypes(self):
        """
        Produce allocationchangerequests with all different change types
        and test that they all display properly
        """
        # create a new allocationchangerequest for each attribute that is changeable

class AllocationNoteCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationNoteCreateView"""

    def setUp(self):
        self.url = f'/allocation/{self.storage_allocation.pk}/allocationnote/add'

    def test_allocationnotecreateview_access(self):
        self.allocation_access_tstbase(self.url)


class AllocationNoteUpdateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationNoteUpdateView"""

    def setUp(self):
        self.storage_allocation_note = AllocationUserNote.objects.create(
            allocation=self.storage_allocation,
            note='test note',
            author=self.admin_user,
        )
        self.url = f'/allocation/allocation-note/{self.storage_allocation_note.pk}/update'

    def test_allocationnoteupdateview_access(self):
        self.allocation_access_tstbase(self.url)
