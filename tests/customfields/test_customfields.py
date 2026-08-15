# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import datetime

from django.core.exceptions import ValidationError

from coldfront.core.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices
from coldfront.core.models import CustomField, CustomFieldChoiceSet, ObjectType
from coldfront.tenancy.filtersets import TenantFilterSet
from coldfront.tenancy.models import Tenant, TenantGroup
from coldfront.utils.testing import TestCase


class CustomFieldTest(TestCase):
    @classmethod
    def setUpTestData(cls):

        Tenant.objects.bulk_create(
            [
                Tenant(name="Tenant A", slug="tenant-a"),
                Tenant(name="Tenant B", slug="tenant-b"),
                Tenant(name="Tenant C", slug="tenant-c"),
            ]
        )

        cls.object_type = ObjectType.objects.get_for_model(Tenant)

    def test_invalid_name(self):
        """
        Try creating a CustomField with an invalid name.
        """
        with self.assertRaises(ValidationError):
            # Invalid character
            CustomField(name="?", type=CustomFieldTypeChoices.TYPE_TEXT).full_clean()
        with self.assertRaises(ValidationError):
            # Double underscores not permitted
            CustomField(name="foo__bar", type=CustomFieldTypeChoices.TYPE_TEXT).full_clean()

    def test_text_field(self):
        value = "Foobar!"

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="text_field", type=CustomFieldTypeChoices.TYPE_TEXT, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_longtext_field(self):
        value = "A" * 256

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(
            name="longtext_field", type=CustomFieldTypeChoices.TYPE_LONGTEXT, required=False
        )
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_integer_field(self):

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="integer_field", type=CustomFieldTypeChoices.TYPE_INTEGER, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        for value in (123456, 0, -123456):
            # Assign a value and check that it is saved
            instance.custom_field_data[cf.name] = value
            instance.save()
            instance.refresh_from_db()
            self.assertEqual(instance.custom_field_data[cf.name], value)

            # Delete the stored value and check that it is now null
            instance.custom_field_data.pop(cf.name)
            instance.save()
            instance.refresh_from_db()
            self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_decimal_field(self):

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="decimal_field", type=CustomFieldTypeChoices.TYPE_DECIMAL, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        for value in (123456.54, 0, -123456.78):
            # Assign a value and check that it is saved
            instance.custom_field_data[cf.name] = value
            instance.save()
            instance.refresh_from_db()
            self.assertEqual(instance.custom_field_data[cf.name], value)

            # Delete the stored value and check that it is now null
            instance.custom_field_data.pop(cf.name)
            instance.save()
            instance.refresh_from_db()
            self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_boolean_field(self):

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="boolean_field", type=CustomFieldTypeChoices.TYPE_INTEGER, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        for value in (True, False):
            # Assign a value and check that it is saved
            instance.custom_field_data[cf.name] = value
            instance.save()
            instance.refresh_from_db()
            self.assertEqual(instance.custom_field_data[cf.name], value)

            # Delete the stored value and check that it is now null
            instance.custom_field_data.pop(cf.name)
            instance.save()
            instance.refresh_from_db()
            self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_date_field(self):
        value = datetime.date(2016, 6, 23)

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="date_field", type=CustomFieldTypeChoices.TYPE_DATE, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = cf.serialize(value)
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.cf[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_datetime_field(self):
        value = datetime.datetime(2016, 6, 23, 9, 45, 0)

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(name="date_field", type=CustomFieldTypeChoices.TYPE_DATETIME, required=False)
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = cf.serialize(value)
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.cf[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_select_field(self):
        CHOICES = (
            "a:Option A",
            "b:Option B",
            "c:Option C",
        )
        value = "a"

        # Create a set of custom field choices
        choice_set = CustomFieldChoiceSet.objects.create(name="Custom Field Choice Set 1", choices=CHOICES)

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(
            name="select_field", type=CustomFieldTypeChoices.TYPE_SELECT, required=False, choice_set=choice_set
        )
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_multiselect_field(self):
        CHOICES = (
            ("a", "Option A"),
            ("b", "Option B"),
            ("c", "Option C"),
        )
        value = ["a", "b"]

        # Create a set of custom field choices
        choice_set = CustomFieldChoiceSet.objects.create(name="Custom Field Choice Set 1", choices=CHOICES)

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(
            name="multiselect_field",
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            required=False,
            choice_set=choice_set,
        )
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_remove_selected_choice(self):
        """
        Removing a ChoiceSet choice that is referenced by an object should raise
        a ValidationError exception.
        """
        CHOICES = (
            "a:Option A",
            "b:Option B",
            "c:Option C",
            "d:Option D",
        )

        # Create a set of custom field choices
        choice_set = CustomFieldChoiceSet.objects.create(name="Custom Field Choice Set 1", choices=CHOICES)

        # Create a select custom field
        cf = CustomField.objects.create(
            name="select_field", type=CustomFieldTypeChoices.TYPE_SELECT, required=False, choice_set=choice_set
        )
        cf.object_types.set([self.object_type])

        # Create a multi-select custom field
        cf_multiselect = CustomField.objects.create(
            name="multiselect_field",
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            required=False,
            choice_set=choice_set,
        )
        cf_multiselect.object_types.set([self.object_type])

        # Assign a choice for both custom fields on an object
        instance = Tenant.objects.first()
        instance.custom_field_data[cf.name] = "a"
        instance.custom_field_data[cf_multiselect.name] = ["b", "c"]
        instance.save()

        # Attempting to delete a selected choice should fail
        with self.assertRaises(ValidationError):
            choice_set.choices = (
                "b:Option B",
                "c:Option C",
                "d:Option D",
            )
            choice_set.full_clean()

        # Attempting to delete either of the multi-select choices should fail
        with self.assertRaises(ValidationError):
            choice_set.choices = (
                "a:Option A",
                "b:Option B",
                "d:Option D",
            )
            choice_set.full_clean()

        # Removing a non-selected choice should succeed
        choice_set.choices = (
            "a:Option A",
            "b:Option B",
            "c:Option C",
        )
        choice_set.full_clean()

    def test_object_field(self):
        value = TenantGroup.objects.create(name="Tenant Group 1", slug="tenant-group-1").pk

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(
            name="object_field",
            type=CustomFieldTypeChoices.TYPE_OBJECT,
            related_object_type=ObjectType.objects.get_for_model(TenantGroup),
            required=False,
        )
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_multiobject_field(self):
        groups = (
            TenantGroup(name="Group 1", slug="group-1"),
            TenantGroup(name="Group 2", slug="group-2"),
            TenantGroup(name="Group 3", slug="group-3"),
        )
        for tenanantgroup in groups:
            tenanantgroup.save()
        value = [group.pk for group in groups]

        # Create a custom field & check that initial value is null
        cf = CustomField.objects.create(
            name="object_field",
            type=CustomFieldTypeChoices.TYPE_MULTIOBJECT,
            related_object_type=ObjectType.objects.get_for_model(TenantGroup),
            required=False,
        )
        cf.object_types.set([self.object_type])
        instance = Tenant.objects.first()
        self.assertIsNone(instance.custom_field_data[cf.name])

        # Assign a value and check that it is saved
        instance.custom_field_data[cf.name] = value
        instance.save()
        instance.refresh_from_db()
        self.assertEqual(instance.custom_field_data[cf.name], value)

        # Delete the stored value and check that it is now null
        instance.custom_field_data.pop(cf.name)
        instance.save()
        instance.refresh_from_db()
        self.assertIsNone(instance.custom_field_data.get(cf.name))

    def test_rename_customfield(self):
        obj_type = ObjectType.objects.get_for_model(Tenant)
        FIELD_DATA = "abc"

        # Create a custom field
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="field1")
        cf.save()
        cf.object_types.set([obj_type])

        # Assign custom field data to an object
        site = Tenant.objects.create(name="Tenant 1", slug="tenant-1", custom_field_data={"field1": FIELD_DATA})
        site.refresh_from_db()
        self.assertEqual(site.custom_field_data["field1"], FIELD_DATA)

        # Rename the custom field
        cf.name = "field2"
        cf.save()

        # Check that custom field data on the object has been updated
        site.refresh_from_db()
        self.assertNotIn("field1", site.custom_field_data)
        self.assertEqual(site.custom_field_data["field2"], FIELD_DATA)

    def test_default_value_validation(self):
        choiceset = CustomFieldChoiceSet.objects.create(
            name="Test Choice Set",
            choices=(
                "choice1:Choice 1",
                "choice2:Choice 2",
            ),
        )
        site = Tenant.objects.create(name="Tenant 1", slug="tenant-1")
        object_type = ObjectType.objects.get_for_model(Tenant)

        # Text
        CustomField(name="test", type="text", required=True, default="Default text").full_clean()

        # Integer
        CustomField(name="test", type="integer", required=True, default=1).full_clean()
        with self.assertRaises(ValidationError):
            CustomField(name="test", type="integer", required=True, default="xxx").full_clean()

        # Boolean
        CustomField(name="test", type="boolean", required=True, default=True).full_clean()
        with self.assertRaises(ValidationError):
            CustomField(name="test", type="boolean", required=True, default="xxx").full_clean()

        # Date
        CustomField(name="test", type="date", required=True, default="2023-02-25").full_clean()
        with self.assertRaises(ValidationError):
            CustomField(name="test", type="date", required=True, default="xxx").full_clean()

        # Datetime
        CustomField(name="test", type="datetime", required=True, default="2023-02-25 02:02:02").full_clean()
        with self.assertRaises(ValidationError):
            CustomField(name="test", type="datetime", required=True, default="xxx").full_clean()

        # Selection
        CustomField(name="test", type="select", required=True, choice_set=choiceset, default="choice1").full_clean()
        with self.assertRaises(ValidationError):
            CustomField(name="test", type="select", required=True, choice_set=choiceset, default="xxx").full_clean()

        # Multi-select
        CustomField(
            name="test",
            type="multiselect",
            required=True,
            choice_set=choiceset,
            default=["choice1"],  # Single default choice
        ).full_clean()
        CustomField(
            name="test",
            type="multiselect",
            required=True,
            choice_set=choiceset,
            default=["choice1", "choice2"],  # Multiple default choices
        ).full_clean()
        with self.assertRaises(ValidationError):
            CustomField(
                name="test", type="multiselect", required=True, choice_set=choiceset, default=["xxx"]
            ).full_clean()

        # Object
        CustomField(
            name="test", type="object", required=True, related_object_type=object_type, default=site.pk
        ).full_clean()
        with self.assertRaises(ValidationError):
            CustomField(
                name="test", type="object", required=True, related_object_type=object_type, default="xxx"
            ).full_clean()

        # Multi-object
        CustomField(
            name="test", type="multiobject", required=True, related_object_type=object_type, default=[site.pk]
        ).full_clean()
        with self.assertRaises(ValidationError):
            CustomField(
                name="test", type="multiobject", required=True, related_object_type=object_type, default=["xxx"]
            ).full_clean()


class CustomFieldManagerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        object_type = ObjectType.objects.get_for_model(Tenant)
        custom_field = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="text_field", default="foo")
        custom_field.save()
        custom_field.object_types.set([object_type])

    def test_get_for_model(self):
        self.assertEqual(CustomField.objects.get_for_model(Tenant).count(), 1)
        self.assertEqual(CustomField.objects.get_for_model(TenantGroup).count(), 0)


class CustomFieldModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cf1 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="foo")
        cf1.save()
        cf1.object_types.set([ObjectType.objects.get_for_model(Tenant)])

        cf2 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="bar")
        cf2.save()
        cf2.object_types.set([ObjectType.objects.get_for_model(TenantGroup)])

    def test_cf_data(self):
        """
        Check that custom field data is present on the instance immediately after being set and after being fetched
        from the database.
        """
        site = Tenant(name="Test Site", slug="test-site")

        # Check custom field data on new instance
        site.custom_field_data["foo"] = "abc"
        self.assertEqual(site.cf["foo"], "abc")

        # Check custom field data from database
        site.save()
        site = Tenant.objects.get(name="Test Site")
        self.assertEqual(site.cf["foo"], "abc")

    def test_invalid_data(self):
        """
        Any invalid or stale custom field data should be removed from the instance.
        """
        site = Tenant(name="Test Site", slug="test-site")

        # Set custom field data
        site.custom_field_data["foo"] = "abc"
        site.custom_field_data["bar"] = "def"
        site.clean()

        self.assertIn("foo", site.custom_field_data)
        self.assertNotIn("bar", site.custom_field_data)

    def test_missing_required_field(self):
        """
        Check that a ValidationError is raised if any required custom fields are not present.
        """
        cf3 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="baz", required=True)
        cf3.save()
        cf3.object_types.set([ObjectType.objects.get_for_model(Tenant)])

        site = Tenant(name="Test Site", slug="test-site")

        # Set custom field data with a required field omitted
        site.custom_field_data["foo"] = "abc"
        with self.assertRaises(ValidationError):
            site.clean()

        site.custom_field_data["baz"] = "def"
        site.clean()


class CustomFieldModelFilterTest(TestCase):
    queryset = Tenant.objects.all()
    filterset = TenantFilterSet

    @classmethod
    def setUpTestData(cls):
        object_type = ObjectType.objects.get_for_model(Tenant)

        groups = (
            TenantGroup(name="Manufacturer 1", slug="manufacturer-1"),
            TenantGroup(name="Manufacturer 2", slug="manufacturer-2"),
            TenantGroup(name="Manufacturer 3", slug="manufacturer-3"),
            TenantGroup(name="Manufacturer 4", slug="manufacturer-4"),
        )
        for tenanantgroup in groups:
            tenanantgroup.save()

        choice_set = CustomFieldChoiceSet.objects.create(
            name="Custom Field Choice Set 1", choices=(("a", "A"), ("b", "B"), ("c", "C"))
        )

        # Integer filtering
        cf = CustomField(name="cf1", type=CustomFieldTypeChoices.TYPE_INTEGER)
        cf.save()
        cf.object_types.set([object_type])

        # Decimal filtering
        cf = CustomField(name="cf2", type=CustomFieldTypeChoices.TYPE_DECIMAL)
        cf.save()
        cf.object_types.set([object_type])

        # Boolean filtering
        cf = CustomField(name="cf3", type=CustomFieldTypeChoices.TYPE_BOOLEAN)
        cf.save()
        cf.object_types.set([object_type])

        # Exact text filtering
        cf = CustomField(
            name="cf4", type=CustomFieldTypeChoices.TYPE_TEXT, filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT
        )
        cf.save()
        cf.object_types.set([object_type])

        # Loose text filtering
        cf = CustomField(
            name="cf5", type=CustomFieldTypeChoices.TYPE_TEXT, filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE
        )
        cf.save()
        cf.object_types.set([object_type])

        # Date filtering
        cf = CustomField(name="cf6", type=CustomFieldTypeChoices.TYPE_DATE)
        cf.save()
        cf.object_types.set([object_type])

        # Selection filtering
        cf = CustomField(name="cf9", type=CustomFieldTypeChoices.TYPE_SELECT, choice_set=choice_set)
        cf.save()
        cf.object_types.set([object_type])

        # Multiselect filtering
        cf = CustomField(name="cf10", type=CustomFieldTypeChoices.TYPE_MULTISELECT, choice_set=choice_set)
        cf.save()
        cf.object_types.set([object_type])

        # Object filtering
        cf = CustomField(
            name="cf11",
            type=CustomFieldTypeChoices.TYPE_OBJECT,
            related_object_type=ObjectType.objects.get_for_model(TenantGroup),
        )
        cf.save()
        cf.object_types.set([object_type])

        # Multi-object filtering
        cf = CustomField(
            name="cf12",
            type=CustomFieldTypeChoices.TYPE_MULTIOBJECT,
            related_object_type=ObjectType.objects.get_for_model(TenantGroup),
        )
        cf.save()
        cf.object_types.set([object_type])

        Tenant.objects.bulk_create(
            [
                Tenant(
                    name="Site 1",
                    slug="site-1",
                    custom_field_data={
                        "cf1": 100,
                        "cf2": 100.1,
                        "cf3": True,
                        "cf4": "foo",
                        "cf5": "foo",
                        "cf6": "2016-06-26",
                        "cf7": "http://a.example.com",
                        "cf8": "http://a.example.com",
                        "cf9": "A",
                        "cf10": ["A", "B"],
                        "cf11": groups[0].pk,
                        "cf12": [groups[0].pk, groups[3].pk],
                    },
                ),
                Tenant(
                    name="Site 2",
                    slug="site-2",
                    custom_field_data={
                        "cf1": 200,
                        "cf2": 200.2,
                        "cf3": True,
                        "cf4": "foobar",
                        "cf5": "foobar",
                        "cf6": "2016-06-27",
                        "cf7": "http://b.example.com",
                        "cf8": "http://b.example.com",
                        "cf9": "B",
                        "cf10": ["B", "C"],
                        "cf11": groups[1].pk,
                        "cf12": [groups[1].pk, groups[3].pk],
                    },
                ),
                Tenant(
                    name="Site 3",
                    slug="site-3",
                    custom_field_data={
                        "cf1": 300,
                        "cf2": 300.3,
                        "cf3": False,
                        "cf4": "bar",
                        "cf5": "bar",
                        "cf6": "2016-06-28",
                        "cf7": "http://c.example.com",
                        "cf8": "http://c.example.com",
                        "cf9": "C",
                        "cf10": None,
                        "cf11": groups[2].pk,
                        "cf12": [groups[2].pk, groups[3].pk],
                    },
                ),
                Tenant(name="Site 4", slug="site-4"),
            ]
        )

    def test_filter_integer(self):
        self.assertEqual(self.filterset({"cf_cf1": 100}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf1__n": [200]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf1__gt": [200]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf1__gte": [200]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf1__lt": [200]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf1__lte": [200]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf1__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_decimal(self):
        self.assertEqual(self.filterset({"cf_cf2": 200.2}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf2__n": [200.2]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf2__gt": [200.2]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf2__gte": [200.2]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf2__lt": [200.2]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf2__lte": [200.2]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf2__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_boolean(self):
        self.assertEqual(self.filterset({"cf_cf3": True}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({"cf_cf3": False}, self.queryset).qs.count(), 1)

    def test_filter_text_strict(self):
        self.assertEqual(self.filterset({"cf_cf4": "foo"}, self.queryset).qs.count(), 1)
        # TODO not supported in sqlite?
        # self.assertEqual(self.filterset({"cf_cf4__n": "foo"}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf4__ic": "foo"}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf4__nic": "foo"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf4__isw": "foo"}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf4__nisw": "foo"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf4__iew": "bar"}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf4__niew": "bar"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf4__ie": "FOO"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf4__nie": "FOO"}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf4__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_text_loose(self):
        self.assertEqual(self.filterset({"cf_cf5": "foo"}, self.queryset).qs.count(), 2)

    def test_filter_date(self):
        self.assertEqual(self.filterset({"cf_cf6": "2016-06-26"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf6__n": ["2016-06-27"]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf6__gt": ["2016-06-27"]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf6__gte": ["2016-06-27"]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf6__lt": ["2016-06-27"]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf6__lte": ["2016-06-27"]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf6__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_select(self):
        self.assertEqual(self.filterset({"cf_cf9": "A"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf9__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_multiselect(self):
        self.assertEqual(self.filterset({"cf_cf10": "A"}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf10": ["A", "C"]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf10": ["null"]}, self.queryset).qs.count(), 1)  # Contains a literal null
        # self.assertEqual(self.filterset({"cf_cf10__empty": True}, self.queryset).qs.count(), 2)

    def test_filter_object(self):
        group_ids = TenantGroup.objects.values_list("id", flat=True)
        self.assertEqual(self.filterset({"cf_cf11": group_ids[1]}, self.queryset).qs.count(), 1)
        # self.assertEqual(self.filterset({"cf_cf11__empty": True}, self.queryset).qs.count(), 1)

    def test_filter_multiobject(self):
        group_ids = TenantGroup.objects.values_list("id", flat=True)
        self.assertEqual(self.filterset({"cf_cf12": group_ids[3]}, self.queryset).qs.count(), 3)
        # self.assertEqual(self.filterset({"cf_cf12": [group_ids[0], group_ids[1]]}, self.queryset).qs.count(), 2)
        # self.assertEqual(self.filterset({"cf_cf12__empty": True}, self.queryset).qs.count(), 1)
