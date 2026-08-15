# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.urls import reverse

from coldfront.core.models import CustomField, CustomFieldChoiceSet, ObjectType
from coldfront.tenancy.models import Tenant
from coldfront.utils.testing import APITestCase, APIViewTestCases


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("core-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class CustomFieldTest(APIViewTestCases.APIViewTestCase):
    model = CustomField
    brief_fields = ["description", "display", "id", "name", "url"]
    create_data = [
        {
            "object_types": ["tenancy.tenant"],
            "name": "cf4",
            "type": "date",
        },
        {
            "object_types": ["tenancy.tenant"],
            "name": "cf5",
            "type": "integer",
        },
        {
            "object_types": ["tenancy.tenant"],
            "name": "cf6",
            "type": "text",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    update_data = {
        "object_types": ["tenancy.tenantgroup"],
        "name": "New_Name",
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        site_ct = ObjectType.objects.get_for_model(Tenant)

        custom_fields = (
            CustomField(name="cf1", type="text"),
            CustomField(name="cf2", type="integer"),
            CustomField(name="cf3", type="boolean"),
        )
        CustomField.objects.bulk_create(custom_fields)
        for cf in custom_fields:
            cf.object_types.add(site_ct)


class CustomFieldChoiceSetTest(APIViewTestCases.APIViewTestCase):
    model = CustomFieldChoiceSet
    brief_fields = ["choices_count", "description", "display", "id", "name", "url"]
    create_data = [
        {
            "name": "Choice Set 4",
            "choices": [
                "4A:Choice 1",
                "4B:Choice 2",
                "4C:Choice 3",
            ],
        },
        {
            "name": "Choice Set 5",
            "choices": [
                "5A:Choice 1",
                "5B:Choice 2",
                "5C:Choice 3",
            ],
        },
        {
            "name": "Choice Set 6",
            "choices": [
                "6A:Choice 1",
                "6B:Choice 2",
                "6C:Choice 3",
            ],
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    update_data = {
        "name": "Choice Set X",
        "choices": [
            "X1:Choice 1",
            "X2:Choice 2",
            "X3:Choice 3",
        ],
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        choice_sets = (
            CustomFieldChoiceSet(
                name="Choice Set 1",
                choices=["1A", "1B", "1C", "1D", "1E"],
            ),
            CustomFieldChoiceSet(
                name="Choice Set 2",
                choices=["2A", "2B", "2C", "2D", "2E"],
            ),
            CustomFieldChoiceSet(
                name="Choice Set 3",
                choices=["3A", "3B", "3C", "3D", "3E"],
            ),
        )
        CustomFieldChoiceSet.objects.bulk_create(choice_sets)
