from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.school.models import School


class TestSchool(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            self.initial_fields = {
                'pk': 11,
                'description': 'Rory Meyers College of Nursing',
            }

            self.unsaved_object = School(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        self.assertEqual(1, len(School.objects.all()))

        school_obj = self.data.unsaved_object
        school_obj.save()

        self.assertEqual(2, len(School.objects.all()))

        retrieved_school = School.objects.get(pk=school_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_school, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(school_obj, retrieved_school)


    def test_description_maxlength(self):
        expected_maximum_length = 255
        maximum_description = 'x' * expected_maximum_length

        school_obj = self.data.unsaved_object

        school_obj.description = maximum_description + 'x'
        with self.assertRaises(ValidationError):
            school_obj.clean_fields()

        school_obj.description = maximum_description
        school_obj.clean_fields()
        school_obj.save()

        retrieved_obj = School.objects.get(pk=school_obj.pk)
        self.assertEqual(maximum_description, retrieved_obj.description)
