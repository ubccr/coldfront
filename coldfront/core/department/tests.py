from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client

from coldfront.core.test_helpers import test_utils
from coldfront.core.department.models import Department, DepartmentMember


FIXTURES = [
            "coldfront/core/test_helpers/test_data/test_fixtures/resources.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/department.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json",
            ]

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
        self.client.force_login(self.dept_manager_user, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/department/")
        self.assertEqual(response.status_code, 200)


    def test_department_list_content(self):
        """Confirm that department-list has correct content
        """

        # non-admins can only see departments they belong to.
        self.client.force_login(self.dept_manager_user, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/department/?show_all_departments=on")
        # print("LIST", response, str(list(response.context['messages'])))

        # admins can see all departments.
        self.client.force_login(self.admin_user, backend="django.contrib.auth.backends.ModelBackend")



class DepartmentDetailViewTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.department = Department.objects.first()
        self.dept_manager_user = DepartmentMember.objects.get(
                                                    role_id=1,
                                                    department_id=self.department.pk
                                                    ).member
        self.client = Client()


    def test_department_detail_access(self):
        """Test department-detail access controls
        """
        dept_id = self.department.pk
        # If not logged in, can't see page; redirect to login page.
        test_utils.test_redirect_to_login(self, f"/department/{dept_id}/")

        # admin can access
        test_utils.test_admin_can_access(self, f"/department/{dept_id}/")

        # user belonging to department can access
        # self.client.force_login(self.dept_manager_user, backend="django.contrib.auth.backends.ModelBackend")
        # response = self.client.get(f"/department/{dept_id}/")
        # print(response)

        # user not belonging to department cannot access

    def test_department_detail_content(self):
        """Check content of department detail pages.
        """
        # department members who are not administrators cannot update department details
        # or review bills
