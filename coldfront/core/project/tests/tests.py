# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from coldfront.core.project.models import (
    Project,
    ProjectAttribute,
    ProjectAttributeType,
)
from coldfront.core.project.utils import (
    determine_automated_institution_choice,
    generate_project_code,
)
from coldfront.core.test_helpers.factories import (
    FieldOfScienceFactory,
    PAttributeTypeFactory,
    ProjectAttributeFactory,
    ProjectAttributeTypeFactory,
    ProjectFactory,
    ProjectStatusChoiceFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)


class TestProject(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            user = UserFactory(username="cgray")
            user.userprofile.is_pi = True

            field_of_science = FieldOfScienceFactory(description="Chemistry")
            status = ProjectStatusChoiceFactory(name="Active")

            self.initial_fields = {
                "pi": user,
                "title": "Angular momentum in QGP holography",
                "description": "We want to estimate the quark chemical potential of a rotating sample of plasma.",
                "field_of_science": field_of_science,
                "status": status,
                "force_review": True,
            }

            self.unsaved_object = Project(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        """Test that generic project fields save correctly"""
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
        """Test that the title field has a maximum length of 255 characters"""
        expected_maximum_length = 255
        maximum_title = "x" * expected_maximum_length

        project_obj = self.data.unsaved_object

        project_obj.title = maximum_title + "x"
        with self.assertRaises(ValidationError):
            project_obj.clean_fields()

        project_obj.title = maximum_title
        project_obj.clean_fields()
        project_obj.save()

        retrieved_obj = Project.objects.get(pk=project_obj.pk)
        self.assertEqual(maximum_title, retrieved_obj.title)

    def test_auto_import_project_title(self):
        """Test that auto-imported projects must have a title"""
        project_obj = self.data.unsaved_object
        assert project_obj.pk is None

        project_obj.title = "Auto-Import Project"
        with self.assertRaises(ValidationError):
            project_obj.clean()

    def test_description_minlength(self):
        """Test that a description must be at least 10 characters long
        If description is less than 10 characters, an error should be raised
        """
        expected_minimum_length = 10
        minimum_description = "x" * expected_minimum_length

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
        """
        Test that project descriptions must be changed from the default value.
        """
        project_obj = self.data.unsaved_object
        assert project_obj.pk is None

        project_obj.description = project_obj.DEFAULT_DESCRIPTION
        with self.assertRaises(ValidationError):
            project_obj.clean()

    def test_pi_foreignkey_on_delete(self):
        """Test that a project is deleted when its PI is deleted."""
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.pi.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))

    def test_fos_foreignkey_on_delete(self):
        """Test that a project is deleted when its field of science is deleted."""
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.field_of_science.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))

    def test_status_foreignkey_on_delete(self):
        """Test that a project is deleted when its status is deleted."""
        project_obj = self.data.unsaved_object
        project_obj.save()

        self.assertEqual(1, len(Project.objects.all()))

        project_obj.status.delete()

        # expecting CASCADE
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(pk=project_obj.pk)
        self.assertEqual(0, len(Project.objects.all()))


class TestProjectAttribute(TestCase):
    @classmethod
    def setUpTestData(cls):
        project_attr_types = [("Project ID", "Text"), ("Account Number", "Int")]
        for atype in project_attr_types:
            ProjectAttributeTypeFactory(
                name=atype[0],
                attribute_type=PAttributeTypeFactory(name=atype[1]),
                has_usage=False,
                is_unique=True,
            )
        cls.project = ProjectFactory()
        cls.new_attr = ProjectAttributeFactory(
            proj_attr_type=ProjectAttributeType.objects.get(name="Account Number"),
            project=cls.project,
            value=1243,
        )

    def test_unique_attrs_one_per_project(self):
        """
        Test that only one attribute of the same attribute type can be
        saved if the attribute type is unique
        """
        self.assertEqual(1, len(self.project.projectattribute_set.all()))
        proj_attr_type = ProjectAttributeType.objects.get(name="Account Number")
        new_attr = ProjectAttribute(project=self.project, proj_attr_type=proj_attr_type)
        with self.assertRaises(ValidationError):
            new_attr.clean()

    def test_attribute_must_match_datatype(self):
        """Test that the attribute value must match the attribute type"""

        proj_attr_type = ProjectAttributeType.objects.get(name="Account Number")
        new_attr = ProjectAttribute(project=self.project, proj_attr_type=proj_attr_type, value="abc")
        with self.assertRaises(ValidationError):
            new_attr.clean()


class TestProjectCode(TransactionTestCase):
    """Tear down database after each run to prevent conflicts across cases"""

    reset_sequences = True

    def setUp(self):
        self.user = UserFactory(username="capeo")
        self.field_of_science = FieldOfScienceFactory(description="Physics")
        self.status = ProjectStatusChoiceFactory(name="Active")

    def create_project_with_code(self, title, project_code, project_code_padding=0):
        """Helper method to create a project and a project code with a specific prefix and padding"""
        # Project Creation
        project = Project.objects.create(
            title=title,
            pi=self.user,
            status=self.status,
            field_of_science=self.field_of_science,
        )

        project.project_code = generate_project_code(project_code, project.pk, project_code_padding)

        project.save()

        return project.project_code

    @patch("coldfront.config.core.PROJECT_CODE", "BFO")
    @patch("coldfront.config.core.PROJECT_CODE_PADDING", 3)
    def test_project_code_increment_after_deletion(self):
        from coldfront.config.core import PROJECT_CODE, PROJECT_CODE_PADDING

        """Test that the project code increments by one after a project is deleted"""

        # Create the first project
        project_with_code_padding1 = self.create_project_with_code("Project 1", PROJECT_CODE, PROJECT_CODE_PADDING)
        self.assertEqual(project_with_code_padding1, "BFO001")

        # Delete the first project
        project_obj1 = Project.objects.get(title="Project 1")
        project_obj1.delete()

        # Create the second project
        project_with_code_padding2 = self.create_project_with_code("Project 2", PROJECT_CODE, PROJECT_CODE_PADDING)
        self.assertEqual(project_with_code_padding2, "BFO002")

    @patch("coldfront.config.core.PROJECT_CODE", "BFO")
    def test_no_padding(self):
        from coldfront.config.core import PROJECT_CODE

        """Test with code and no padding"""
        project_with_code = self.create_project_with_code("Project 1", PROJECT_CODE)
        self.assertEqual(project_with_code, "BFO1")  # No padding

    @patch("coldfront.config.core.PROJECT_CODE", "BFO")
    @patch("coldfront.config.core.PROJECT_CODE_PADDING", 3)
    def test_different_prefix_padding(self):
        from coldfront.config.core import PROJECT_CODE, PROJECT_CODE_PADDING

        """Test with code and padding"""

        # Create two projects with codes
        project_with_code_padding1 = self.create_project_with_code("Project 1", PROJECT_CODE, PROJECT_CODE_PADDING)
        project_with_code_padding2 = self.create_project_with_code("Project 2", PROJECT_CODE, PROJECT_CODE_PADDING)

        # Test the generated project codes
        self.assertEqual(project_with_code_padding1, "BFO001")
        self.assertEqual(project_with_code_padding2, "BFO002")


class TestInstitution(TestCase):
    def setUp(self):
        self.user = UserFactory(username="capeo")
        self.field_of_science = FieldOfScienceFactory(description="Physics")
        self.status = ProjectStatusChoiceFactory(name="Active")

    def create_project_with_institution(self, title, institution_dict=None):
        """Helper method to create a project and assign a institution value based on the argument passed"""
        # Project Creation
        project = Project.objects.create(
            title=title,
            pi=self.user,
            status=self.status,
            field_of_science=self.field_of_science,
        )

        if institution_dict:
            determine_automated_institution_choice(project, institution_dict)

        project.save()

        return project.institution

    @patch(
        "coldfront.config.core.PROJECT_INSTITUTION_EMAIL_MAP",
        {"inst.ac.com": "AC", "inst.edu.com": "EDU", "bfo.ac.uk": "BFO"},
    )
    def test_institution_is_none(self):
        from coldfront.config.core import PROJECT_INSTITUTION_EMAIL_MAP

        """Test to check if institution is none after both env vars are enabled. """

        # Create project with both institution
        project_institution = self.create_project_with_institution("Project 1", PROJECT_INSTITUTION_EMAIL_MAP)

        # Create the first project
        self.assertEqual(project_institution, "None")

    @patch(
        "coldfront.config.core.PROJECT_INSTITUTION_EMAIL_MAP",
        {"inst.ac.com": "AC", "inst.edu.com": "EDU", "bfo.ac.uk": "BFO"},
    )
    def test_institution_multiple_users(self):
        from coldfront.config.core import PROJECT_INSTITUTION_EMAIL_MAP

        """Test to check multiple projects with different user email addresses, """

        # Create project for user 1
        self.user.email = "user@inst.ac.com"
        self.user.save()
        project_institution_one = self.create_project_with_institution("Project 1", PROJECT_INSTITUTION_EMAIL_MAP)
        self.assertEqual(project_institution_one, "AC")

        # Create project for user 2
        self.user.email = "user@bfo.ac.uk"
        self.user.save()
        project_institution_two = self.create_project_with_institution("Project 2", PROJECT_INSTITUTION_EMAIL_MAP)
        self.assertEqual(project_institution_two, "BFO")

        # Create project for user 3
        self.user.email = "user@inst.edu.com"
        self.user.save()
        project_institution_three = self.create_project_with_institution("Project 3", PROJECT_INSTITUTION_EMAIL_MAP)
        self.assertEqual(project_institution_three, "EDU")

    @patch(
        "coldfront.config.core.PROJECT_INSTITUTION_EMAIL_MAP",
        {"inst.ac.com": "AC", "inst.edu.com": "EDU", "bfo.ac.uk": "BFO"},
    )
    def test_determine_automated_institution_choice_does_not_save_to_database(self):
        from coldfront.config.core import PROJECT_INSTITUTION_EMAIL_MAP

        """Test that the function only modifies project in memory, not in database"""

        self.user.email = "user@inst.ac.com"
        self.user.save()

        # Create project, similar to create_project_with_institution, but without the save function.
        project = Project.objects.create(
            title="Test Project",
            pi=self.user,
            status=self.status,
            field_of_science=self.field_of_science,
            institution="Default",
        )

        original_db_project = Project.objects.get(id=project.id)
        self.assertEqual(original_db_project.institution, "Default")

        # Call the function and check object was modified in memory.
        determine_automated_institution_choice(project, PROJECT_INSTITUTION_EMAIL_MAP)
        self.assertEqual(project.institution, "AC")

        # Check that database was NOT modified
        current_db_project = Project.objects.get(id=project.id)
        self.assertEqual(original_db_project.institution, "Default")

        self.assertNotEqual(project.institution, current_db_project.institution)
