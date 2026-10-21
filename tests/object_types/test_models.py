# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from coldfront.core.models import ObjectType
from coldfront.users.models import Group, User


class ObjectTypeTest(TestCase):
    def test_create(self):
        """
        Test that an ObjectType created for a given app_label & model name will be automatically assigned to
        the appropriate ContentType.
        """
        kwargs = {
            "app_label": "foo",
            "model": "bar",
        }
        ct = ContentType.objects.create(**kwargs)
        ot = ObjectType.objects.create(**kwargs)
        self.assertEqual(ot.contenttype_ptr, ct)

    def test_get_by_natural_key(self):
        """
        Test that get_by_natural_key() returns the appropriate ObjectType.
        """
        self.assertEqual(
            ObjectType.objects.get_by_natural_key("users", "user"),
            ObjectType.objects.get(app_label="users", model="user"),
        )
        with self.assertRaises(ObjectDoesNotExist):
            ObjectType.objects.get_by_natural_key("foo", "bar")

    def test_get_for_id(self):
        """
        Test that get_by_id() returns the appropriate ObjectType.
        """
        ot = ObjectType.objects.get_by_natural_key("users", "group")
        self.assertEqual(ObjectType.objects.get_for_id(ot.pk), ObjectType.objects.get(pk=ot.pk))
        with self.assertRaises(ObjectDoesNotExist):
            ObjectType.objects.get_for_id(0)

    def test_get_for_model(self):
        """
        Test that get_by_model() returns the appropriate ObjectType.
        """
        self.assertEqual(ObjectType.objects.get_for_model(User), ObjectType.objects.get_by_natural_key("users", "user"))

    def test_get_for_models(self):
        """
        Test that get_by_models() returns the appropriate ObjectType mapping.
        """
        self.assertEqual(
            ObjectType.objects.get_for_models(User, Group),
            {
                User: ObjectType.objects.get_by_natural_key("users", "user"),
                Group: ObjectType.objects.get_by_natural_key("users", "group"),
            },
        )

    def test_public(self):
        """
        Test that public() returns only ObjectTypes for public models.
        """
        public_ots = ObjectType.objects.public()
        self.assertIn(ObjectType.objects.get_by_natural_key("users", "user"), public_ots)
        self.assertNotIn(ObjectType.objects.get_by_natural_key("auth", "permission"), public_ots)

    def test_with_feature(self):
        """
        Test with_feature() returns only ObjectTypes whose ``features``
        JSON dict has the given feature set to ``True``.

        Exercises the ``KT`` / JSON-extraction path, which must translate the
        stored JSON boolean to the Python string 'true' consistently across
        backends (sqlite/postgres/mariadb). Rows with the feature ``False``,
        absent, or ``None`` must be excluded.
        """
        ot_true = ObjectType.objects.create(app_label="probe_a", model="m", features={"cloning": True})
        ot_false = ObjectType.objects.create(app_label="probe_b", model="m", features={"cloning": False})
        ot_absent = ObjectType.objects.create(app_label="probe_c", model="m", features={})
        ot_none = ObjectType.objects.create(app_label="probe_d", model="m", features={"cloning": None})

        result = ObjectType.objects.with_feature("cloning")
        self.assertIn(ot_true, result)
        self.assertNotIn(ot_false, result)
        self.assertNotIn(ot_absent, result)
        self.assertNotIn(ot_none, result)
