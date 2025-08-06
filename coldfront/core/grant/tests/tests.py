# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.core.grant.models import Grant
from coldfront.core.test_helpers.factories import (
    GrantFundingAgencyFactory,
    GrantStatusChoiceFactory,
    ProjectFactory,
)


class TestGrant(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            project = ProjectFactory()
            grantFundingAgency = GrantFundingAgencyFactory(name="Department of Defense (DoD)")
            grantStatusChoice = GrantStatusChoiceFactory(name="Active")

            start_date = datetime.date.today()
            end_date = start_date + relativedelta(days=900)

            self.initial_fields = {
                "project": project,
                "title": "Quantum Halls",
                "grant_number": "12345",
                "role": "PI",
                "grant_pi_full_name": "Stephanie Foster",
                "funding_agency": grantFundingAgency,
                "grant_start": start_date,
                "grant_end": end_date,
                "percent_credit": 20.0,
                "direct_funding": 200000.0,
                "total_amount_awarded": 1000000.0,
                "status": grantStatusChoice,
            }

            self.unsaved_object = Grant(**self.initial_fields)

    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        self.assertEqual(0, len(Grant.objects.all()))

        grant_obj = self.data.unsaved_object
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        retrieved_fos = Grant.objects.get(pk=grant_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_fos, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(grant_obj, retrieved_fos)

    def test_title_minlength(self):
        expected_minimum_length = 3
        minimum_title = "x" * expected_minimum_length

        grant_obj = self.data.unsaved_object

        grant_obj.title = minimum_title[:-1]
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.title = minimum_title
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(minimum_title, retrieved_obj.title)

    def test_title_maxlength(self):
        expected_maximum_length = 255
        maximum_title = "x" * expected_maximum_length

        grant_obj = self.data.unsaved_object

        grant_obj.title = maximum_title + "x"
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.title = maximum_title
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(maximum_title, retrieved_obj.title)

    def test_grant_number_minlength(self):
        expected_minimum_length = 3
        minimum_grant_number = "1" * expected_minimum_length

        grant_obj = self.data.unsaved_object

        grant_obj.grant_number = minimum_grant_number[:-1]
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.grant_number = minimum_grant_number
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(minimum_grant_number, retrieved_obj.grant_number)

    def test_grant_number_maxlength(self):
        expected_maximum_length = 255
        maximum_grant_number = "1" * expected_maximum_length

        grant_obj = self.data.unsaved_object

        grant_obj.grant_number = maximum_grant_number + "1"
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.grant_number = maximum_grant_number
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(maximum_grant_number, retrieved_obj.grant_number)

    def test_grant_pi_maxlength(self):
        expected_maximum_length = 255
        maximum_grant_pi_full_name = "x" * expected_maximum_length

        grant_obj = self.data.unsaved_object

        grant_obj.grant_pi_full_name = maximum_grant_pi_full_name + "x"
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.grant_pi_full_name = maximum_grant_pi_full_name
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(maximum_grant_pi_full_name, retrieved_obj.grant_pi_full_name)

    def test_grant_pi_optional(self):
        self.assertEqual(0, len(Grant.objects.all()))

        grant_obj = self.data.unsaved_object
        grant_obj.grant_pi_full_name = ""
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual("", retrieved_obj.grant_pi_full_name)

    def test_other_funding_agency_maxlength(self):
        expected_maximum_length = 255
        maximum_other_funding_agency = "x" * expected_maximum_length

        grant_obj = self.data.unsaved_object

        grant_obj.other_funding_agency = maximum_other_funding_agency + "x"
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.other_funding_agency = maximum_other_funding_agency
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(maximum_other_funding_agency, retrieved_obj.other_funding_agency)

    def test_other_funding_agency_optional(self):
        self.assertEqual(0, len(Grant.objects.all()))

        grant_obj = self.data.unsaved_object
        grant_obj.other_funding_agency = ""
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual("", retrieved_obj.other_funding_agency)

    def test_other_award_number_maxlength(self):
        expected_maximum_length = 255
        maxiumum_other_award_number = "1" * expected_maximum_length

        grant_obj = self.data.unsaved_object

        grant_obj.other_award_number = maxiumum_other_award_number + "1"
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.other_award_number = maxiumum_other_award_number
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(maxiumum_other_award_number, retrieved_obj.other_award_number)

    def test_other_award_number_optional(self):
        self.assertEqual(0, len(Grant.objects.all()))

        grant_obj = self.data.unsaved_object
        grant_obj.other_award_number = ""
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual("", retrieved_obj.other_award_number)

    def test_percent_credit_maxvalue(self):
        expected_maximum_value = 100

        grant_obj = self.data.unsaved_object

        grant_obj.percent_credit = expected_maximum_value + 1
        with self.assertRaises(ValidationError):
            grant_obj.clean_fields()

        grant_obj.percent_credit = expected_maximum_value
        grant_obj.clean_fields()
        grant_obj.save()

        retrieved_obj = Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(expected_maximum_value, retrieved_obj.percent_credit)

    def test_project_foreignkey_on_delete(self):
        grant_obj = self.data.unsaved_object
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        grant_obj.project.delete()

        # expecting CASCADE
        with self.assertRaises(Grant.DoesNotExist):
            Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(0, len(Grant.objects.all()))

    def test_funding_agency_foreignkey_on_delete(self):
        grant_obj = self.data.unsaved_object
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        grant_obj.funding_agency.delete()

        # expecting CASCADE
        with self.assertRaises(Grant.DoesNotExist):
            Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(0, len(Grant.objects.all()))

    def test_status_foreignkey_on_delete(self):
        grant_obj = self.data.unsaved_object
        grant_obj.save()

        self.assertEqual(1, len(Grant.objects.all()))

        grant_obj.status.delete()

        # expecting CASCADE
        with self.assertRaises(Grant.DoesNotExist):
            Grant.objects.get(pk=grant_obj.pk)
        self.assertEqual(0, len(Grant.objects.all()))
