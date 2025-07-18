# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.test import TestCase

from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import (
    PAttributeTypeFactory,
    ProjectAttributeFactory,
    ProjectAttributeTypeFactory,
    ProjectFactory,
    ProjectStatusChoiceFactory,
    ProjectUserFactory,
    ProjectUserRoleChoiceFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)


class ProjectViewTestBase(TestCase):
    """Base class for project view tests"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        cls.backend = "django.contrib.auth.backends.ModelBackend"
        cls.project = ProjectFactory(status=ProjectStatusChoiceFactory(name="Active"))

        user_role = ProjectUserRoleChoiceFactory(name="User")
        project_user = ProjectUserFactory(project=cls.project, role=user_role)
        cls.project_user = project_user.user

        manager_role = ProjectUserRoleChoiceFactory(name="Manager")
        pi_user = ProjectUserFactory(project=cls.project, role=manager_role, user=cls.project.pi)
        cls.pi_user = pi_user.user
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        cls.nonproject_user = UserFactory(is_staff=False, is_superuser=False)

        attributetype = PAttributeTypeFactory(name="string")
        cls.projectattributetype = ProjectAttributeTypeFactory(attribute_type=attributetype)

    def project_access_tstbase(self, url):
        """Test basic access control for project views. For all project views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        # If not logged in, can't see page; redirect to login page.
        utils.test_logged_out_redirect_to_login(self, url)
        # after login, pi and admin can access create page
        utils.test_user_can_access(self, self.admin_user, url)


class ProjectDetailViewTest(ProjectViewTestBase):
    """tests for ProjectDetailView"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectDetailViewTest, cls).setUpTestData()
        cls.url = f"/project/{cls.project.pk}/"

    def test_projectdetail_access(self):
        """Test project detail page access"""
        # logged-out user gets redirected, admin can access create page
        self.project_access_tstbase(self.url)
        # pi and projectuser can access
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.project_user, self.url)
        # user not belonging to project cannot access
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)

    def test_projectdetail_permissions(self):
        """Test project detail page access permissions"""
        # admin has is_allowed_to_update_project set to True
        response = utils.login_and_get_page(self.client, self.admin_user, self.url)
        self.assertEqual(response.context["is_allowed_to_update_project"], True)
        # pi has is_allowed_to_update_project set to True
        response = utils.login_and_get_page(self.client, self.pi_user, self.url)
        self.assertEqual(response.context["is_allowed_to_update_project"], True)
        # non-manager user has is_allowed_to_update_project set to False
        response = utils.login_and_get_page(self.client, self.project_user, self.url)
        self.assertEqual(response.context["is_allowed_to_update_project"], False)

    def test_projectdetail_request_allocation_button_visibility(self):
        """Test visibility of projectdetail request allocation button across user levels"""
        button_text = "Request Resource Allocation"
        # admin can see request allocation button
        utils.page_contains_for_user(self, self.admin_user, self.url, button_text)
        # pi can see request allocation button
        utils.page_contains_for_user(self, self.pi_user, self.url, button_text)
        # non-manager user cannot see request allocation button
        utils.page_does_not_contain_for_user(self, self.project_user, self.url, button_text)

    def test_projectdetail_edituser_button_visibility(self):
        """Test visibility of projectdetail edit button across user levels"""
        # admin can see edit button
        utils.page_contains_for_user(self, self.admin_user, self.url, "fa-user-edit")
        # pi can see edit button
        utils.page_contains_for_user(self, self.pi_user, self.url, "fa-user-edit")
        # non-manager user cannot see edit button
        utils.page_does_not_contain_for_user(self, self.project_user, self.url, "fa-user-edit")

    def test_projectdetail_addnotification_button_visibility(self):
        """Test visibility of projectdetail add notification button across user levels"""
        # admin can see add notification button
        utils.page_contains_for_user(self, self.admin_user, self.url, "Add Notification")
        # pi cannot see add notification button
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, "Add Notification")
        # non-manager user cannot see add notification button
        utils.page_does_not_contain_for_user(self, self.project_user, self.url, "Add Notification")


class ProjectCreateTest(ProjectViewTestBase):
    """Tests for project create view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectCreateTest, cls).setUpTestData()
        cls.url = "/project/create/"

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
        int_attributetype = PAttributeTypeFactory(name="Int")
        cls.int_projectattributetype = ProjectAttributeTypeFactory(attribute_type=int_attributetype)
        cls.url = f"/project/{cls.project.pk}/project-attribute-create/"

    def test_project_access(self):
        """Test access to project attribute create page"""
        # logged-out user gets redirected, admin can access create page
        self.project_access_tstbase(self.url)
        # pi can access create page
        utils.test_user_can_access(self, self.pi_user, self.url)
        # project user and nonproject user cannot access create page
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)

    def test_project_attribute_create_post(self):
        """Test project attribute creation post response"""

        self.client.force_login(self.admin_user, backend=self.backend)
        response = self.client.post(
            self.url,
            data={"proj_attr_type": self.projectattributetype.pk, "value": "test_value", "project": self.project.pk},
        )
        redirect_url = f"/project/{self.project.pk}/"
        self.assertRedirects(response, redirect_url, status_code=302, target_status_code=200)

    def test_project_attribute_create_post_required_values(self):
        """ProjectAttributeCreate correctly flags missing project or value"""
        self.client.force_login(self.admin_user, backend=self.backend)
        # missing project
        response = self.client.post(
            self.url, data={"proj_attr_type": self.projectattributetype.pk, "value": "test_value"}
        )
        self.assertFormError(response, "form", "project", "This field is required.")
        # missing value
        response = self.client.post(
            self.url, data={"proj_attr_type": self.projectattributetype.pk, "project": self.project.pk}
        )
        self.assertFormError(response, "form", "value", "This field is required.")

    def test_project_attribute_create_value_type_match(self):
        """ProjectAttributeCreate correctly flags value-type mismatch"""

        self.client.force_login(self.admin_user, backend=self.backend)
        # test that value must be numeric if proj_attr_type is string
        response = self.client.post(
            self.url,
            data={"proj_attr_type": self.int_projectattributetype.pk, "value": True, "project": self.project.pk},
        )
        self.assertContains(response, "Invalid Value True. Value must be an int.")


class ProjectAttributeUpdateTest(ProjectViewTestBase):
    """Tests for ProjectAttributeUpdateView"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectAttributeUpdateTest, cls).setUpTestData()
        cls.projectattribute = ProjectAttributeFactory(
            value=36238, proj_attr_type=cls.projectattributetype, project=cls.project
        )
        cls.url = f"/project/{cls.project.pk}/project-attribute-update/{cls.projectattribute.pk}"

    def test_project_attribute_update_access(self):
        """Test access to project attribute update page"""
        self.project_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        # project user, pi, and nonproject user cannot access update page
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectAttributeDeleteTest(ProjectViewTestBase):
    """Tests for ProjectAttributeDeleteView"""

    @classmethod
    def setUpTestData(cls):
        """set up users and project for testing"""
        super(ProjectAttributeDeleteTest, cls).setUpTestData()
        cls.projectattribute = ProjectAttributeFactory(
            value=36238, proj_attr_type=cls.projectattributetype, project=cls.project
        )
        cls.url = f"/project/{cls.project.pk}/project-attribute-delete/"

    def test_project_attribute_delete_access(self):
        """test access to project attribute delete page"""
        # logged-out user gets redirected, admin can access delete page
        self.project_access_tstbase(self.url)
        # pi can access delete page
        utils.test_user_can_access(self, self.pi_user, self.url)
        # project user and nonproject user cannot access delete page
        utils.test_user_cannot_access(self, self.project_user, self.url)
        utils.test_user_cannot_access(self, self.nonproject_user, self.url)


class ProjectListViewTest(ProjectViewTestBase):
    """Tests for ProjectList view"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(ProjectListViewTest, cls).setUpTestData()
        # add 100 projects to test pagination, permissions, search functionality
        additional_projects = [ProjectFactory() for i in list(range(100))]
        cls.additional_projects = [p for p in additional_projects if p.pi.last_name != cls.project.pi.last_name]
        cls.url = "/project/"

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
        """Project list displays only projects that user is an active member of"""
        # deactivated projectuser won't see project on their page
        response = utils.login_and_get_page(self.client, self.project_user, self.url)
        self.assertEqual(len(response.context["object_list"]), 1)
        proj_user = self.project.projectuser_set.get(user=self.project_user)
        proj_user.status, _ = ProjectUserStatusChoice.objects.get_or_create(name="Removed")
        proj_user.save()
        response = utils.login_and_get_page(self.client, self.project_user, self.url)
        self.assertEqual(len(response.context["object_list"]), 0)

    def test_project_list_displayall_permission_admin(self):
        """Projectlist displayall option displays all projects to admin"""
        url = self.url + "?show_all_projects=on"
        response = utils.login_and_get_page(self.client, self.admin_user, url)
        self.assertGreaterEqual(101, len(response.context["object_list"]))

    def test_project_list_displayall_permission_pi(self):
        """Projectlist displayall option displays only the pi's projects to the pi"""
        url = self.url + "?show_all_projects=on"
        response = utils.login_and_get_page(self.client, self.pi_user, url)
        self.assertEqual(len(response.context["object_list"]), 1)

    def test_project_list_displayall_permission_project_user(self):
        """Projectlist displayall displays only projects projectuser belongs to"""
        url = self.url + "?show_all_projects=on"
        response = utils.login_and_get_page(self.client, self.project_user, url)
        self.assertEqual(len(response.context["object_list"]), 1)

    ### ProjectListView search tests ###

    def test_project_list_search(self):
        """Test that project list search works."""
        url_base = self.url + "?show_all_projects=on"
        url = (
            f"{url_base}&last_name={self.project.pi.last_name}"
            + f"&field_of_science={self.project.field_of_science.description}"
        )
        # search by project project_title
        response = utils.login_and_get_page(self.client, self.admin_user, url)
        self.assertEqual(len(response.context["object_list"]), 1)


class ProjectRemoveUsersViewTest(ProjectViewTestBase):
    """Tests for ProjectRemoveUsersView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = f"/project/{self.project.pk}/remove-users/"

    def test_projectremoveusersview_access(self):
        """test access to project remove users page"""
        self.project_access_tstbase(self.url)


class ProjectUpdateViewTest(ProjectViewTestBase):
    """Tests for ProjectUpdateView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = f"/project/{self.project.pk}/update/"

    def test_projectupdateview_access(self):
        """test access to project update page"""
        self.project_access_tstbase(self.url)


class ProjectReviewListViewTest(ProjectViewTestBase):
    """Tests for ProjectReviewListView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = "/project/project-review-list"

    def test_projectreviewlistview_access(self):
        """test access to project review list page"""
        self.project_access_tstbase(self.url)


class ProjectArchivedListViewTest(ProjectViewTestBase):
    """Tests for ProjectArchivedListView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = "/project/archived/"

    def test_projectarchivedlistview_access(self):
        """test access to project archived list page"""
        self.project_access_tstbase(self.url)


class ProjectNoteCreateViewTest(ProjectViewTestBase):
    """Tests for ProjectNoteCreateView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = f"/project/{self.project.pk}/projectnote/add"

    def test_projectnotecreateview_access(self):
        """test access to project note create page"""
        self.project_access_tstbase(self.url)


class ProjectAddUsersSearchView(ProjectViewTestBase):
    """Tests for ProjectAddUsersSearchView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = f"/project/{self.project.pk}/add-users-search/"

    def test_projectadduserssearchview_access(self):
        """test access to project add users search page"""
        self.project_access_tstbase(self.url)


class ProjectUserDetailViewTest(ProjectViewTestBase):
    """Tests for ProjectUserDetailView"""

    def setUp(self):
        """set up users and project for testing"""
        self.url = f"/project/{self.project.pk}/user-detail/{self.project_user.pk}"

    def test_projectuserdetailview_access(self):
        """test access to project user detail page"""
        self.project_access_tstbase(self.url)
