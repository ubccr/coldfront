import logging
from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from coldfront.core.test_helpers import test_utils
from coldfront.core.department.models import Department, DepartmentMember

FIXTURES = [
            "coldfront/core/test_helpers/test_data/test_fixtures/resources.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/department.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/kohn_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/gordon_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json",
            ]

logging.disable(logging.ERROR)

class DepartmentListViewTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.dept_manager_user = get_user_model().objects.get(username='eostrom')
        self.client = Client()

    def test_department_list_access(self):
        """Test department list access controls."""
        # If not logged in, can't see page; redirect to login page.
        test_utils.test_redirect_to_login(self, "/department/")

        # after login, user and admin can access list page
        test_utils.test_user_can_access(self, self.admin_user, "/department/")
        test_utils.test_user_can_access(self, self.dept_manager_user, "/department/")


    def test_department_list_content(self):
        """Confirm that department-list has correct content
        """
        # admins can see all departments.
        response = test_utils.login_and_get_page(
                self.client, self.admin_user, "/department/?show_all_departments=on")
        self.assertEqual(len(response.context['object_list']), 2)
        self.assertEqual([i.name for i in response.context['object_list'].all()],
                        ['School of Maths and Sciences', 'Computational Chemistry'])

        # non-admins can only see departments they belong to.
        response = test_utils.login_and_get_page(
                self.client, self.dept_manager_user, "/department/?show_all_departments=on")
        self.assertEqual(len(response.context['object_list']), 1)
        self.assertEqual(response.context['object_list'].first().name, 'School of Maths and Sciences')


class DepartmentDetailViewTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.department = Department.objects.first()
        self.dept_manager_user = DepartmentMember.objects.get(
                                                    role="approver",
                                                    organization_id=self.department.id
                                                    ).member
        self.dept_member_user = DepartmentMember.objects.get(
                                                    role="user",
                                                    organization_id=self.department.id
                                                    ).member
        self.nondept_user = get_user_model().objects.get(username='sdpoisson')
        self.client = Client()


    def test_department_detail_access(self):
        """Test department-detail access controls
        """
        url = f"/department/{self.department.pk}/"
        # If not logged in, can't see page; redirect to login page.
        test_utils.test_redirect_to_login(self, url)

        # admin can access
        test_utils.test_user_can_access(self, self.admin_user, url)
        # manager user belonging to department can access
        test_utils.test_user_can_access(self, self.dept_manager_user, url)
        # non-manager user belonging to department can access
        test_utils.test_user_can_access(self, self.dept_member_user, url)

        # user not belonging to department cannot access
        response = test_utils.login_and_get_page(self.client, self.nondept_user, url)
        self.assertEqual(response.status_code, 403)



    def test_department_detail_content(self):
        """Check content of department detail pages.
        """
        url = f"/department/{self.department.pk}/"
        response = test_utils.login_and_get_page(self.client, self.admin_user, url)
        # print("response ADMIN:", response.context, "\n\n")
        # confirm that all projects are visible
        self.assertEqual(len(response.context['projects']), 2)

        # department members who are not administrators cannot update department details
        # or review bills
        response = test_utils.login_and_get_page(self.client, self.dept_user, url)
        # print("response USER:", response.context, "\n\n")
        # confirm that only the user's projects are visible
        self.assertEqual(len(response.context['projects']), 1)
