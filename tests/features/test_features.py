# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase

from coldfront.core.models import ObjectType, Tag
from coldfront.tenancy.models import Tenant, TenantGroup


class BasicFeaturesTest(TestCase):
    def test_has_feature(self):
        """
        Test the functionality of the ObjectType.has_feature() utility function.
        """
        # Sanity checking
        self.assertTrue(hasattr(Tenant, "clone"), "Invalid test?")

        self.assertTrue(ObjectType.has_feature(Tenant, "cloning"))
        self.assertTrue(ObjectType.has_feature(Tenant, "change_logging"))

    def test_get_model_features(self):
        """
        Check that ObjectType.get_model_features() returns the expected features for a model.
        """
        # Sanity checking
        self.assertTrue(hasattr(Tenant, "clone"), "Invalid test?")

        features = ObjectType.get_model_features(Tenant)
        self.assertIn("cloning", features)
        self.assertIn("change_logging", features)

    def test_cloningmixin(self):
        """
        Test basic functionality of the CloningMixin
        """
        group = TenantGroup.objects.create(name="Test Group", slug="test-group")
        tenant = Tenant.objects.create(name="Test", description="test desc", group=group)
        attrs = tenant.clone()
        self.assertEqual(attrs["group"], tenant.group_id)
        self.assertEqual(attrs["description"], tenant.description)
        self.assertNotIn("name", attrs)
        self.assertNotIn("slug", attrs)

    def test_tag_weights(self):
        """
        Test tag weights to ensure correct ordering
        """
        Tag.objects.create(name="Tag 1", slug="tag-1", weight=3000)
        Tag.objects.create(name="Tag 2", slug="tag-2")  # Default: 1000
        Tag.objects.create(name="Tag 3", slug="tag-3", weight=2000)
        Tag.objects.create(name="Tag 4", slug="tag-4", weight=2000)

        tags = Tag.objects.all()

        self.assertEqual(tags[0].slug, "tag-2")
        self.assertEqual(tags[1].slug, "tag-3")
        self.assertEqual(tags[2].slug, "tag-4")
        self.assertEqual(tags[3].slug, "tag-1")

    def test_tag_related_manager(self):
        """
        Test adding tags to a model
        """
        tags = [
            Tag.objects.create(name="Tag 1", slug="tag-1", weight=3000),
            Tag.objects.create(name="Tag 2", slug="tag-2"),  # Default: 1000
            Tag.objects.create(name="Tag 3", slug="tag-3", weight=2000),
            Tag.objects.create(name="Tag 4", slug="tag-4", weight=2000),
        ]

        tenant = Tenant.objects.create(name="Test")
        for _tag in tags:
            tenant.tags.add(_tag)
        tenant.save()

        tenant = Tenant.objects.first()
        tags = tenant.tags.all()

        self.assertEqual(tags[0].slug, "tag-2")
        self.assertEqual(tags[1].slug, "tag-3")
        self.assertEqual(tags[2].slug, "tag-4")
        self.assertEqual(tags[3].slug, "tag-1")
