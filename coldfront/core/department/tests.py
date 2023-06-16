import logging
from django.contrib.auth import get_user_model
from django.test import TestCase

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models
from coldfront.core.test_helpers.fasrc_factories import setup_departments
from coldfront.core.department.models import Department

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

logging.disable(logging.ERROR)

class DepartmentViewTest(TestCase):
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests.
        """
        setup_models(cls)
        setup_departments(cls)

class DepartmentListViewTest(DepartmentViewTest):

    def setUp(self):
        self.dept_manager_user = get_user_model().objects.get(username='eostrom')

    def test_department_list_access(self):
        """Test department list access controls."""
        # If not logged in, can't see page; redirect to login page.
        utils.test_logged_out_redirect_to_login(self, "/department/")

        # after login, user and admin can access list page
        utils.test_user_can_access(self, self.admin_user, "/department/")
        utils.test_user_can_access(self, self.dept_manager_user, "/department/")


    def test_department_list_content(self):
        """Confirm that department-list has correct content
        """
        # admins can see all departments.
        response = utils.login_and_get_page(
            self.client, self.admin_user, "/department/?show_all_departments=on"
        )
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertEqual(
            [i.name for i in response.context['object_list'].all()],
            ['School of Maths and Sciences', 'Computational Chemistry']
        )

        # non-admins can only see departments they belong to.
        response = utils.login_and_get_page(
            self.client, self.dept_manager_user, "/department/?show_all_departments=on"
        )
        self.assertEqual(len(response.context['object_list']), 1)
        self.assertEqual(
            response.context['object_list'].first().name, 'School of Maths and Sciences'
        )


class DepartmentDetailViewTest(DepartmentViewTest):

    def setUp(self):
        self.department = Department.objects.first()
        # self.dept_member_user = DepartmentMember.objects.get(
        #                                 role="user",
        #                                 organization_id=self.department.id
        #                                 ).member
        self.dept_manager_user = get_user_model().objects.get(username='eostrom')
        self.nondept_user = self.pi_user
        self.url = f"/department/{self.department.pk}/"


    def test_department_detail_access(self):
        """Test department-detail access controls
        """
        # If not logged in, can't see page; redirect to login page.
        utils.test_logged_out_redirect_to_login(self, self.url)

        # admin can access
        utils.test_user_can_access(self, self.admin_user, self.url)
        # manager user belonging to department can access
        utils.test_user_can_access(self, self.dept_manager_user, self.url)
        # non-manager user belonging to department can access
        dept = Department.objects.get(name="Computational Chemistry")
        url = f"/department/{dept.pk}/"

        utils.test_user_can_access(self, self.admin_user, url)
        utils.test_user_can_access(self, self.dept_member_user, url)

        # user not belonging to department cannot access
        response = utils.login_and_get_page(self.client, self.nondept_user, self.url)
        self.assertEqual(response.status_code, 403)


    def test_department_detail_content(self):
        """Check content of department detail pages.
        """
        response = utils.login_and_get_page(self.client, self.admin_user, self.url)
        # print("response ADMIN:", [f'{i}\n' for i in response.context], "\n\n")
        # confirm that all projects are visible
        self.assertEqual(len(response.context['projects']), 2)
        # department members who are not administrators cannot update department details
        # or review bills

    def test_department_detail_content_dept_member(self):
        dept = Department.objects.get(name="Computational Chemistry")
        url = f"/department/{dept.pk}/"
        response = utils.login_and_get_page(self.client, self.dept_member_user, url)
        #print("response USER:", response.context, "\n\n")
        # confirm that only the user's projects are visible
        self.assertEqual(len(response.context['projects']), 1)
