# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import reverse

from coldfront.core.models import Tag, TaggedItem
from coldfront.tenancy.models import Tenant
from coldfront.utils.testing import APITestCase, APIViewTestCases


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("core-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class TagTest(APIViewTestCases.APIViewTestCase):
    model = Tag
    brief_fields = ["color", "description", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Tag 4",
            "slug": "tag-4",
            "weight": 1000,
        },
        {
            "name": "Tag 5",
            "slug": "tag-5",
        },
        {
            "name": "Tag 6",
            "slug": "tag-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        tags = (
            Tag(name="Tag 1", slug="tag-1"),
            Tag(name="Tag 2", slug="tag-2"),
            Tag(name="Tag 3", slug="tag-3", weight=26),
        )
        Tag.objects.bulk_create(tags)


class TaggedItemTest(APIViewTestCases.GetObjectViewTestCase, APIViewTestCases.ListObjectsViewTestCase):
    model = TaggedItem
    brief_fields = ["display", "id", "object", "object_id", "object_type", "tag", "url"]

    @classmethod
    def setUpTestData(cls):

        tags = (
            Tag(name="Tag 1", slug="tag-1"),
            Tag(name="Tag 2", slug="tag-2"),
            Tag(name="Tag 3", slug="tag-3"),
        )
        Tag.objects.bulk_create(tags)

        tenants = (
            Tenant(name="Tenant 1", slug="Tenant-1"),
            Tenant(name="Tenant 2", slug="Tenant-2"),
            Tenant(name="Tenant 3", slug="Tenant-3"),
        )
        Tenant.objects.bulk_create(tenants)
        tenants[0].tags.set([tags[0], tags[1]])
        tenants[1].tags.set([tags[1], tags[2]])
        tenants[2].tags.set([tags[2], tags[0]])
