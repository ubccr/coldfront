from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.test_helpers.factories import (
    FieldOfScienceFactory,
    ProjectStatusChoiceFactory,
    UserFactory,
)

from coldfront.core.project.models import Project

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

