# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.utils import timezone

from coldfront.core.choices import ObjectChangeActionChoices
from coldfront.tenancy.models import Tenant


class BasicChangeLoggingTest(TestCase):
    def test_on_create(self):
        """
        Test action create functionality of the ChangeLoggingMixin
        """
        obj = Tenant.objects.create(name="test1")
        objectchange = obj.to_objectchange(ObjectChangeActionChoices.ACTION_CREATE)
        self.assertIsNone(objectchange.prechange_data)
        self.assertEqual(objectchange.postchange_data["name"], "test1")

    def test_on_update(self):
        """
        Test action update functionality of the ChangeLoggingMixin
        """
        obj = Tenant.objects.create(name="test1")
        obj.snapshot()
        obj.name = "Test2 changed"
        obj.created = timezone.now()
        obj.last_updated = timezone.now()

        objectchange = obj.to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(objectchange.prechange_data["name"], "test1")
        self.assertEqual(objectchange.postchange_data["name"], "Test2 changed")
        diff = objectchange.diff()
        self.assertEqual(diff["pre"]["name"], "test1")
        self.assertEqual(diff["post"]["name"], "Test2 changed")
        self.assertNotIn("created", diff["pre"])
        self.assertNotIn("last_updated", diff["pre"])
        self.assertNotIn("created", diff["post"])
        self.assertNotIn("last_updated", diff["post"])
