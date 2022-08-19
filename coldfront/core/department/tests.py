from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client


from coldfront.core.department.models import Department


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
        self.test_user1 = get_user_model().objects.get(username='gvanrossum')
        self.test_user2 = get_user_model().objects.get(username='eostrom')
        self.client = Client()

    def test_department_list_access(self):
        """Test department-list access controls
        """
        # no login means redirect
        response = self.client.get("/department/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/user/login?next=/department/")

        # after login, user and admin can access list page
        self.client.force_login(self.test_user2, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/department/")
        self.assertEqual(response.status_code, 200)


    def test_department_list_content(self):
        """Confirm that department-list has correct content
        """
        self.client.force_login(self.test_user2, backend="django.contrib.auth.backends.ModelBackend")

        # non-admins can't see all departments.
        response = self.client.get("/department/?show_all_departments=on")
        print("LIST", response, str(list(response.context['messages'])))

        # admins can see all departments


class DepartmentDetailViewTest(TestCase):
    fixtures = FIXTURES

    def setUp(self):
        self.test_user1 = get_user_model().objects.get(username='gvanrossum')
        # eostrom has connection with dept 1
        self.test_user2 = get_user_model().objects.get(username='eostrom')
        self.client = Client()


    def test_department_detail_access(self):
        """Test department-detail access controls
        """
        response = self.client.get("/department/1/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/user/login?next=/department/1/")

        # admin can access
        self.client.force_login(self.test_user1, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/department/1/")
        self.assertEqual(response.status_code, 200)

        # user belonging to department can access
        self.client.force_login(self.test_user2, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/department/1/")
        print(response)

        # user not belonging to department cannot access
