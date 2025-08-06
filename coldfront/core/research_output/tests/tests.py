# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.test_helpers.factories import (
    ProjectFactory,
    UserFactory,
)


class TestResearchOutput(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            project = ProjectFactory()
            user = UserFactory(username="submitter")

            self.initial_fields = {
                "project": project,
                "title": "Something we made!",
                "description": "something, really",
                "created_by": user,
            }
            self.unsaved_object = ResearchOutput(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        self.assertEqual(0, len(ResearchOutput.objects.all()))

        research_output_obj = self.data.unsaved_object
        research_output_obj.save()

        self.assertEqual(1, len(ResearchOutput.objects.all()))

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_obj, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(research_output_obj, retrieved_obj)

    def test_title_optional(self):
        self.assertEqual(0, len(ResearchOutput.objects.all()))

        research_output_obj = self.data.unsaved_object
        research_output_obj.title = ""
        research_output_obj.save()

        self.assertEqual(1, len(ResearchOutput.objects.all()))

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertEqual("", retrieved_obj.title)

    def test_empty_title_sanitized(self):
        research_output_obj = self.data.unsaved_object
        research_output_obj.title = "        \t\n        "
        research_output_obj.save()

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertEqual("", retrieved_obj.title)

    def test_description_minlength(self):
        expected_minimum_length = 3
        minimum_description = "x" * expected_minimum_length

        research_output_obj = self.data.unsaved_object

        research_output_obj.description = minimum_description[:-1]
        with self.assertRaises(ValidationError):
            research_output_obj.clean_fields()

        research_output_obj.description = minimum_description
        research_output_obj.clean_fields()
        research_output_obj.save()

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertEqual(minimum_description, retrieved_obj.description)

    def test_created_by_required_initially(self):
        research_output_obj = self.data.unsaved_object
        assert research_output_obj.pk is None

        research_output_obj.created_by = None
        with self.assertRaises(ValueError):
            research_output_obj.save()

    def test_created_by_can_be_nulled(self):
        research_output_obj = self.data.unsaved_object
        research_output_obj.save()

        research_output_obj.created_by = None
        research_output_obj.save()

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertIsNone(retrieved_obj.created_by)

    def test_created_by_foreignkey_on_delete(self):
        research_output_obj = self.data.unsaved_object
        research_output_obj.save()

        research_output_obj.created_by.delete()

        try:
            retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        except ResearchOutput.DoesNotExist as e:
            raise self.failureException("Expected no cascade from user deletion") from e

        # if here, did not cascade
        self.assertIsNone(retrieved_obj.created_by)  # null, as expected from SET_NULL

    def test_project_foreignkey_on_delete(self):
        research_output_obj = self.data.unsaved_object
        research_output_obj.save()

        self.assertEqual(1, len(ResearchOutput.objects.all()))

        research_output_obj.project.delete()

        # expecting CASCADE
        with self.assertRaises(ResearchOutput.DoesNotExist):
            ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertEqual(0, len(ResearchOutput.objects.all()))

    def test_created_date(self):
        research_output_obj = self.data.unsaved_object
        assert research_output_obj.created is None
        research_output_obj.save()

        retrieved_obj = ResearchOutput.objects.get(pk=research_output_obj.pk)
        self.assertIsInstance(retrieved_obj.created, datetime.datetime)
