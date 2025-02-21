import logging

from django.test import TestCase, tag, override_settings
from django.urls import reverse
from unittest.mock import patch

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import (
    setup_models,
    ProjectFactory,
    PAttributeTypeFactory,
    ProjectAttributeFactory,
    ProjectStatusChoiceFactory,
    ProjectAttributeTypeFactory,
)
from coldfront.core.project.models import (
    Project, ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice
)

logging.disable(logging.CRITICAL)

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

class ProjectViewTestBase(TestCase):
    """Base class for project view tests"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        setup_models(cls)
        cls.project_user = cls.proj_allocationuser
        cls.nonproject_user = cls.nonproj_allocationuser
        # add pi_user and project_user to project_user

        attributetype = PAttributeTypeFactory(name='string')
        cls.projectattributetype = ProjectAttributeTypeFactory(attribute_type=attributetype)# ProjectAttributeType.objects.get(pk=1)

    def project_access_tstbase(self, url):
        """Test basic access control for project views. For all project views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        # If not logged in, can't see page; redirect to login page.
        utils.test_logged_out_redirect_to_login(self, url)
        # after login, pi and admin can access create page
        utils.test_user_can_access(self, self.admin_user, url)


class ArchivedProjectViewsTest(ProjectViewTestBase):
    """tests for Views of an archived project"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ArchivedProjectViewsTest, cls).setUpTestData()
        cls.project.status = ProjectStatusChoiceFactory(name='Archived')
        cls.project.save()

    def test_projectdetail_warning_visible(self):
        """Test that warning is visible on archived project detail page"""
        url = f'/project/{self.project.pk}/'
        utils.page_contains_for_user(self, self.pi_user, url, 'You cannot make any changes')

    def test_projectlist_no_archived_projects(self):
        """Test that archived projects are not visible on project list page"""
        url = '/project/?show_all_projects=True&'
        response = utils.login_and_get_page(self.client, self.pi_user, url)
        self.assertNotContains(response, self.project.title)

    def test_archived_projectlist(self):
        """Test that archived projects are visible on archived project list page"""
        url = '/project/archived/'#?show_all_projects=True&'
        utils.page_contains_for_user(self, self.pi_user, url, self.project.title)


class ProjectArchiveProjectViewTest(ProjectViewTestBase):
    """Tests for project archive project view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectArchiveProjectViewTest, cls).setUpTestData()
        cls.url = f'/project/{cls.project.pk}/archive'

    def test_project_archive_project_access(self):
        """Test access to project archive project page"""
        # logged-out user gets redirected, admin can access archive project page
        self.project_access_tstbase(self.url)
        # pi, projectuser and nonproject user cannot access archive project page
        utils.test_user_cannot_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectCreateTest(ProjectViewTestBase):
    """Tests for project create view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectCreateTest, cls).setUpTestData()
        cls.url = '/project/create/'

    def test_project_access(self):
        """Test access to project create page"""
        # logged-out user gets redirected, admin can access create page
        self.project_access_tstbase(self.url)
        # pi, projectuser and nonproject user cannot access create page
        utils.test_user_cannot_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectAttributeCreateTest(ProjectViewTestBase):
    """Tests for project attribute create view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectAttributeCreateTest, cls).setUpTestData()
        int_attributetype = PAttributeTypeFactory(name='Int')
        cls.int_projectattributetype = ProjectAttributeTypeFactory(attribute_type=int_attributetype)
        cls.url = f'/project/{cls.project.pk}/project-attribute-create/'

    def test_project_access(self):
        """Test access to project attribute create page"""
        # logged-out user gets redirected, admin can access create page
        self.project_access_tstbase(self.url)
        # pi, project user and nonproject user cannot access create page
        utils.test_user_cannot_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)

    def test_project_attribute_create_post(self):
        """Test project attribute creation post response"""

        self.client.force_login(self.admin_user,
                    backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.post(self.url, data={
                                'proj_attr_type': self.projectattributetype.pk,
                                'value': 'test_value',
                                'project': self.project.pk
                                })
        self.assertRedirects(response, f'/project/{self.project.pk}/', status_code=302, target_status_code=200)

    def test_project_attribute_create_post_required_values(self):
        """ProjectAttributeCreate correctly flags missing project or value
        """
        self.client.force_login(self.admin_user,
                    backend='django.contrib.auth.backends.ModelBackend')
        # missing project
        response = self.client.post(self.url, data={
            'proj_attr_type': self.projectattributetype.pk, 'value': 'test_value'
        })
        self.assertFormError(response, 'form', 'project', 'This field is required.')
        # missing value
        response = self.client.post(self.url, data={
            'proj_attr_type': self.projectattributetype.pk, 'project': self.project.pk
        })
        self.assertFormError(response, 'form', 'value', 'This field is required.')

    def test_project_attribute_create_value_type_match(self):
        """ProjectAttributeCreate correctly flags value-type mismatch"""
        self.client.force_login(self.admin_user,
                    backend='django.contrib.auth.backends.ModelBackend')
        # test that value must be numeric if proj_attr_type is string
        response = self.client.post(self.url, data={
            'proj_attr_type': self.int_projectattributetype.pk,
            'value': True,
            'project': self.project.pk
        })
        self.assertContains(response, 'Invalid Value True. Value must be an int.')


class ProjectAttributeUpdateTest(ProjectViewTestBase):

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectAttributeUpdateTest, cls).setUpTestData()
        cls.projectattribute = ProjectAttributeFactory(
            value=36238, proj_attr_type=cls.projectattributetype, project=cls.project
        )
        cls.url = f'/project/{cls.project.pk}/project-attribute-update/{cls.projectattribute.pk}'

    def test_project_attribute_update_access(self):
        """Test access to project attribute update page"""
        self.project_access_tstbase(self.url)
        # project user, pi, and nonproject user cannot access update page
        utils.test_user_cannot_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectAttributeDeleteTest(ProjectViewTestBase):
    """Tests for ProjectAttributeDeleteView"""

    @classmethod
    def setUpTestData(cls):
        """set up users and project for testing"""
        super(ProjectAttributeDeleteTest, cls).setUpTestData()
        cls.projectattribute = ProjectAttributeFactory(value=36238, proj_attr_type=cls.projectattributetype, project=cls.project)
        cls.url = f'/project/{cls.project.pk}/project-attribute-delete/'

    def test_project_attribute_delete_access(self):
        """test access to project attribute delete page"""
        # logged-out user gets redirected, admin can access delete page
        self.project_access_tstbase(self.url)
        # pi, project user and nonproject user cannot access delete page
        utils.test_user_cannot_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectListViewTest(ProjectViewTestBase):
    """Tests for projectlist view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectListViewTest, cls).setUpTestData()
        # add 100 projects to test pagination, permissions, search functionality
        cls.additional_projects = [ProjectFactory() for i in list(range(100))]
        cls.url = '/project/'

    ### ProjectListView access tests ###

    def test_project_list_access(self):
        """Test project list access controls."""
        # logged-out user gets redirected, admin can access list page
        self.project_access_tstbase(self.url)
        # all other users can access list page
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.project_user, self.url)
        utils.test_user_can_access(self, self.nonproject_user, self.url)

    ### ProjectListView display tests ###

    def test_project_list_display_members(self):
        """Test that project list displays only projects that user is an active member of."""
        # deactivated projectuser won't see project on their page
        self.npu.status, _ = ProjectUserStatusChoice.objects.get_or_create(name='Removed')
        self.npu.save()
        response = utils.login_and_get_page(self.client, self.normal_projuser, self.url)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_project_list_displayall_permission_admin(self):
        """Test that the projectlist displayall option displays all projects to admin"""
        url = self.url + '?show_all_projects=on'
        response = utils.login_and_get_page(self.client, self.admin_user, url)
        self.assertEqual(len(response.context['object_list']), Project.objects.all().count())

    def test_project_list_displayall_permission_pi(self):
        """Test that the projectlist displayall option displays only the pi's projects to the pi"""
        url = self.url + '?show_all_projects=on'
        response = utils.login_and_get_page(self.client, self.pi_user, url)
        self.assertEqual(len(response.context['object_list']), 1)

    def test_project_list_displayall_permission_project_user(self):
        """Test that the projectlist displayall option displays only the project user's projects to the project user"""
        url = self.url + '?show_all_projects=on'
        response = utils.login_and_get_page(self.client, self.project_user, url)
        self.assertEqual(len(response.context['object_list']), 1)

    ### ProjectListView search tests ###

    def test_project_list_search(self):
        """Test that project list search works."""
        url_base = self.url + '?show_all_projects=on'
        # search by project project_title
        url = url_base + '&title=' + self.project.title
        response = utils.login_and_get_page(self.client, self.admin_user, url)
        self.assertEqual(len(response.context['object_list']), 1)

    def test_project_list_search_pagination(self):
        """confirm that navigation to next page of search works as expected"""
        url = self.url + '?show_all_projects=on'
        response = utils.login_and_get_page(self.client, self.admin_user, url)


class ProjectRemoveUsersViewTest(ProjectViewTestBase):
    """Tests for ProjectRemoveUsersView"""

    def setUp(self):
        """Set up users and project for testing"""
        super().setUp()
        self.url = reverse('project-remove-users', kwargs={'pk': self.project.pk})
        self.project_user = self.proj_allocationuser
        self.nonproject_user = self.nonproj_allocationuser

    @tag('net')
    def test_projectremoveusersview_access(self):
        """test access to project remove users page"""
        self.project_access_tstbase(self.url)

    @tag('net')
    def test_pi_user_cannot_be_removed(self):
        """Test that the project PI cannot be removed"""
        self.client.force_login(self.pi_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        context = response.context

        users_to_remove = context['formset'].initial
        self.assertNotIn(self.pi_user.username, [u['username'] for u in users_to_remove])


class ProjectUpdateViewTest(ProjectViewTestBase):
    """Tests for ProjectUpdateView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/{self.project.pk}/update/'

    def test_projectupdateview_access(self):
        """test access to project update page"""
        self.project_access_tstbase(self.url)


class ProjectReviewListViewTest(ProjectViewTestBase):
    """Tests for ProjectReviewListView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/project-review-list'

    def test_projectreviewlistview_access(self):
        """test access to project review list page"""
        self.project_access_tstbase(self.url)


class ProjectArchivedListViewTest(ProjectViewTestBase):
    """Tests for ProjectArchivedListView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/archived/'

    def test_projectarchivedlistview_access(self):
        """test access to project archived list page"""
        self.project_access_tstbase(self.url)


class ProjectNoteCreateViewTest(ProjectViewTestBase):
    """Tests for ProjectNoteCreateView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/{self.project.pk}/projectnote/add'

    def test_projectnotecreateview_access(self):
        """test access to project note create page"""
        self.project_access_tstbase(self.url)


class ProjectAddUsersSearchViewTest(ProjectViewTestBase):
    """Tests for ProjectAddUsersSearchView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/{self.project.pk}/add-users-search/'

    def test_projectadduserssearchview_access(self):
        """test access to project add users search page"""
        self.project_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)# pi can access
        utils.test_user_can_access(self, self.proj_accessmanager, self.url)# access manager can access
        utils.test_user_cannot_access(self, self.proj_datamanager, self.url)# data manager cannot access
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.url)# user cannot access

class ProjectAddUsersViewTest(ProjectViewTestBase):
    """Tests for ProjectAddUsersView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = reverse('project-add-users', kwargs={'pk': self.project.pk})
        self.form_data = {
            'q': self.nonproj_allocationuser.username,
            'search_by': 'username_only',
            'userform-TOTAL_FORMS': '1',
            'userform-INITIAL_FORMS': '0',
            'userform-MIN_NUM_FORMS': '0',
            'userform-MAX_NUM_FORMS': '1',
            'userform-0-selected': 'on',
            'userform-0-role': ProjectUserRoleChoice.objects.get(name='User').pk,
            'allocationform-allocation': [self.storage_allocation.pk]
        }

    @override_settings(PLUGIN_LDAP=True)
    def test_projectaddusers_ldapsignalfail_messages(self):
        """Test the messages displayed when the add user signal fails"""
        self.client.force_login(self.pi_user)

    @patch('coldfront.core.project.signals.project_make_projectuser.send')
    def test_projectaddusers_form_validation(self, mock_signal):
        """Test that the formset and allocation form are validated correctly"""
        self.client.force_login(self.proj_accessmanager)
        mock_signal.return_value = None
        # Prepare form data for adding a user
        response = self.client.post(self.url, data=self.form_data)
        self.assertEqual(response.url, reverse('project-detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 302)
        # Check that user was added
        self.assertTrue(ProjectUser.objects.filter(project=self.project, user=self.nonproj_allocationuser).exists())

    @patch('coldfront.core.project.signals.project_make_projectuser.send')
    def test_projectaddusers_signal_fail(self, mock_signal):
        """Test that the add users form fails when the signal sent to LDAP fails"""
        self.client.force_login(self.proj_accessmanager)
        mock_signal.side_effect = Exception("LDAP error occurred")
        # Prepare form data for adding a user
        response = self.client.post(self.url, data=self.form_data, follow=True)
        self.assertContains(response, 'LDAP error occurred')
        self.assertContains(response, 'Added 0 users')


class ProjectUserDetailViewTest(ProjectViewTestBase):
    """Tests for ProjectUserDetailView"""
    def setUp(self):
        """set up users and project for testing"""
        self.url = f'/project/{self.project.pk}/user-detail/{self.project_user.pk}'

    def test_projectuserdetailview_access(self):
        """test access to project user detail page"""
        self.project_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)# pi can access
        utils.test_user_can_access(self, self.proj_generalmanager, self.url) # general manager can access
        utils.test_user_cannot_access(self, self.proj_accessmanager, self.url)# access manager cannot access
        utils.test_user_cannot_access(self, self.proj_datamanager, self.url)# storage manager cannot access

    def test_projectuserdetailview_role_options(self):
        """Only Admin and PI should see option to set role to General Manager;
        option to set role to PI should not be available"""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('project_user_update_form', response.context)
        form = response.context['project_user_update_form']
        self.assertIn('role', form.fields)
        role_field = form.fields['role']
        role_names = [role.name for role in role_field.choices.queryset]
        self.assertNotIn('PI', role_names)
        self.assertIn('General Manager', role_names)
        self.assertIn('Access Manager', role_names)
        self.assertIn('Storage Manager', role_names)

        self.client.force_login(self.pi_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('project_user_update_form', response.context)
        form = response.context['project_user_update_form']
        self.assertIn('role', form.fields)
        role_field = form.fields['role']
        role_names = [role.name for role in role_field.choices.queryset]
        self.assertNotIn('PI', role_names)
        self.assertIn('General Manager', role_names)
        self.assertIn('Access Manager', role_names)
        self.assertIn('Storage Manager', role_names)

        self.client.force_login(self.proj_generalmanager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('project_user_update_form', response.context)
        form = response.context['project_user_update_form']
        self.assertIn('role', form.fields)
        role_field = form.fields['role']
        role_names = [role.name for role in role_field.choices.queryset]
        self.assertNotIn('PI', role_names)
        self.assertNotIn('General Manager', role_names)
        self.assertIn('Access Manager', role_names)
        self.assertIn('Storage Manager', role_names)
