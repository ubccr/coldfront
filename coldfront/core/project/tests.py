from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import (
    FieldOfScienceFactory,
    ProjectStatusChoiceFactory,
    UserFactory,
)

from coldfront.core.project.models import Project

FIXTURES = [
            "coldfront/core/test_helpers/test_data/test_fixtures/resources.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/kohn_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json",
            "coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json",
            ]

class ProjectListViewTest(TestCase):
    """tests for projectlist view"""
    fixtures = FIXTURES

    def setUp(self):
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.client = Client()


    def test_project_list_access(self):
        """Test project list access controls."""
        # If not logged in, can't see page; redirect to login page.
        utils.test_redirect_to_login(self, "/project/")

        # after login, user and admin can access list page
        utils.test_user_can_access(self, self.admin_user, "/project/")


    def test_project_list_search_pagination(self):
        """confirm that navigation to next page of search works as expected"""
        self.client.force_login(self.admin_user, backend="django.contrib.auth.backends.ModelBackend")
        response = self.client.get("/project/?last_name=&username=&field_of_science=SEAS&show_all_projects=on")
        # print(response.context)


class ProjectDetailViewTest(TestCase):
    """tests for projectdetail view"""
    fixtures = FIXTURES

    def setUp(self):
        self.project = Project.objects.get(pk=1)
        self.admin_user = get_user_model().objects.get(username='gvanrossum')
        self.pi_user = get_user_model().objects.get(username='sdpoisson')
        self.project_user = get_user_model().objects.get(username='ljbortkiewicz')
        self.nonproject_user = get_user_model().objects.get(username='wkohn')
        self.client = Client()

    def test_project_detail_access(self):
        """Test project detail page access
        """
        url = f"/project/{self.project.pk}/"
        # If not logged in, can't see page; redirect to login page.
        utils.test_redirect_to_login(self, url)

        # admin can access
        utils.test_user_can_access(self, self.admin_user, url)
        # pi user can access
        utils.test_user_can_access(self, self.pi_user, url)
        # non-manager user belonging to project can access
        utils.test_user_can_access(self, self.project_user, url)

        # user not belonging to project cannot access
        response = utils.login_and_get_page(self.client, self.nonproject_user, url)
        self.assertEqual(response.status_code, 403)


    def test_project_detail_permissions(self):
        """Test project detail permissions
        """
        url = f"/project/{self.project.pk}/"

        # admin has is_allowed_to_update_project set to True
        response = utils.login_and_get_page(self.client, self.admin_user, url)
        self.assertEqual(response.context['is_allowed_to_update_project'], True)

        # pi has is_allowed_to_update_project set to True
        response = utils.login_and_get_page(self.client, self.pi_user, url)
        self.assertEqual(response.context['is_allowed_to_update_project'], True)

        # non-manager user has is_allowed_to_update_project set to False
        response = utils.login_and_get_page(self.client, self.project_user, url)
        self.assertEqual(response.context['is_allowed_to_update_project'], False)



class TestProject(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            user = UserFactory(username='cgray')
            user.userprofile.is_pi = True
            user.save()

            fos = FieldOfScienceFactory(description='Chemistry')
            status = ProjectStatusChoiceFactory(name='Active')


            self.initial_fields = {
                'pi': user,
                'title': 'Angular momentum in QGP holography',
                'description': 'We want to estimate the quark chemical potential of a rotating sample of plasma.',
                'field_of_science': fos,
                'status': status,
                'force_review': True
            }

            self.unsaved_object = Project(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        self.assertEqual(0, len(Project.objects.all()))

        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        retrieved_project = Project.objects.get(pk=project_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_project, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(project_obj, retrieved_project)

    def test_title_maxlength(self):
        expected_maximum_length = 255
        maximum_title = 'x' * expected_maximum_length

        project_obj = self.data.unsaved_object

        project_obj.title = maximum_title + 'x'
        with self.assertRaises(ValidationError):
            project_obj.clean_fields()

        project_obj.title = maximum_title
        project_obj.clean_fields()
        project_obj.save()

        retrieved_obj = Project.objects.get(pk=project_obj.pk)
        self.assertEqual(maximum_title, retrieved_obj.title)

    def test_auto_import_project_title(self):
        project_obj = self.data.unsaved_object
        assert project_obj.pk is None

        project_obj.title = 'Auto-Import Project'
        with self.assertRaises(ValidationError):
            project_obj.clean()

    def test_description_minlength(self):
        expected_minimum_length = 10
        minimum_description = 'x' * expected_minimum_length

        project_obj = self.data.unsaved_object

        project_obj.description = minimum_description[:-1]
        with self.assertRaises(ValidationError):
            project_obj.clean_fields()

        project_obj.description = minimum_description
        project_obj.clean_fields()
        project_obj.save()

        retrieved_obj = Project.objects.get(pk=project_obj.pk)
        self.assertEqual(minimum_description, retrieved_obj.description)

    def test_description_update_required_initially(self):
        project_obj = self.data.unsaved_object
        assert project_obj.pk is None

        project_obj.description = project_obj.DEFAULT_DESCRIPTION
        with self.assertRaises(ValidationError):
            project_obj.clean()

    def test_pi_foreignkey_on_delete(self):
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.pi.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))

    def test_fos_foreignkey_on_delete(self):
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.field_of_science.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))

    def test_status_foreignkey_on_delete(self):
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.status.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))
