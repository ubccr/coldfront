# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.test_helpers.factories import FieldOfScienceFactory


class TestFieldOfScience(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            self.initial_fields = {
                "pk": 11,
                "parent_id": FieldOfScienceFactory(),
                "is_selectable": False,
                "description": "Astronomical Sciences",
                "fos_nsf_id": 120,
                "fos_nsf_abbrev": "AST",
                "directorate_fos_id": 1,
            }

            self.unsaved_object = FieldOfScience(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        self.assertEqual(1, len(FieldOfScience.objects.all()))

        fos_obj = self.data.unsaved_object
        fos_obj.save()

        self.assertEqual(2, len(FieldOfScience.objects.all()))

        retrieved_fos = FieldOfScience.objects.get(pk=fos_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_fos, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(fos_obj, retrieved_fos)

    def test_nsf_id_optional(self):
        self.assertEqual(1, len(FieldOfScience.objects.all()))

        fos_obj = self.data.unsaved_object
        fos_obj.fos_nsf_id = None
        fos_obj.save()

        self.assertEqual(2, len(FieldOfScience.objects.all()))

        retrieved_obj = FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual(None, retrieved_obj.fos_nsf_id)

    def test_nsf_abbrev_optional(self):
        self.assertEqual(1, len(FieldOfScience.objects.all()))

        fos_obj = self.data.unsaved_object
        fos_obj.fos_nsf_abbrev = ""
        fos_obj.save()

        self.assertEqual(2, len(FieldOfScience.objects.all()))

        retrieved_obj = FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual("", retrieved_obj.fos_nsf_abbrev)

    def test_directorate_fos_id_optional(self):
        self.assertEqual(1, len(FieldOfScience.objects.all()))

        fos_obj = self.data.unsaved_object
        fos_obj.directorate_fos_id = None
        fos_obj.save()

        self.assertEqual(2, len(FieldOfScience.objects.all()))

        retrieved_obj = FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual(None, retrieved_obj.directorate_fos_id)

    def test_description_maxlength(self):
        expected_maximum_length = 255
        maximum_description = "x" * expected_maximum_length

        fos_obj = self.data.unsaved_object

        fos_obj.description = maximum_description + "x"
        with self.assertRaises(ValidationError):
            fos_obj.clean_fields()

        fos_obj.description = maximum_description
        fos_obj.clean_fields()
        fos_obj.save()

        retrieved_obj = FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual(maximum_description, retrieved_obj.description)

    def test_nsf_abbrev_maxlength(self):
        expected_maximum_length = 10
        maximum_nsf_abbrev = "x" * expected_maximum_length

        fos_obj = self.data.unsaved_object

        fos_obj.fos_nsf_abbrev = maximum_nsf_abbrev + "x"
        with self.assertRaises(ValidationError):
            fos_obj.clean_fields()

        fos_obj.fos_nsf_abbrev = maximum_nsf_abbrev
        fos_obj.clean_fields()
        fos_obj.save()

        retrieved_obj = FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual(maximum_nsf_abbrev, retrieved_obj.fos_nsf_abbrev)

    def test_parent_id_foreignkey_on_delete(self):
        fos_obj = self.data.unsaved_object
        fos_obj.save()

        self.assertEqual(2, len(FieldOfScience.objects.all()))

        fos_obj.parent_id.delete()

        # expecting CASCADE
        with self.assertRaises(FieldOfScience.DoesNotExist):
            FieldOfScience.objects.get(pk=fos_obj.pk)
        self.assertEqual(0, len(FieldOfScience.objects.all()))
