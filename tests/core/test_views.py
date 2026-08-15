# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.messages import get_messages
from django.urls import reverse

from coldfront.core.models import ObjectType, SavedFilter, TableConfig, Tag
from coldfront.tenancy.models import Tenant
from coldfront.utils.testing import ViewTestCases


class SavedFilterTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SavedFilter

    @classmethod
    def setUpTestData(cls):
        tenant_type = ObjectType.objects.get_for_model(Tenant)

        users = (
            Tenant(name="Tenant 1", slug="tenant-1"),
            Tenant(name="Tenant 2", slug="tenant-2"),
            Tenant(name="Tenant 3", slug="tenant-3"),
        )
        for user in users:
            user.save()

        saved_filters = (
            SavedFilter(
                name="Saved Filter 1",
                slug="saved-filter-1",
                user=None,
                weight=100,
                parameters={"status": ["active"]},
            ),
            SavedFilter(
                name="Saved Filter 2",
                slug="saved-filter-2",
                user=None,
                weight=200,
                parameters={"status": ["planned"]},
            ),
            SavedFilter(
                name="Saved Filter 3",
                slug="saved-filter-3",
                user=None,
                weight=300,
                parameters={"status": ["retired"]},
            ),
        )
        SavedFilter.objects.bulk_create(saved_filters)
        for i, savedfilter in enumerate(saved_filters):
            savedfilter.object_types.set([tenant_type])

        cls.form_data = {
            "name": "Saved Filter X",
            "slug": "saved-filter-x",
            "object_types": [tenant_type.pk],
            "description": "Foo",
            "weight": 1000,
            "enabled": True,
            "shared": True,
            "parameters": '{"foo": 123}',
        }

        cls.csv_data = (
            "name,slug,object_types,weight,enabled,shared,parameters",
            'Saved Filter 4,saved-filter-4,tenancy.tenant,400,True,True,{"foo": "a"}',
            'Saved Filter 5,saved-filter-5,tenancy.tenant,500,True,True,{"foo": "b"}',
            'Saved Filter 6,saved-filter-6,tenancy.tenant,600,True,True,{"foo": "c"}',
        )

        cls.csv_update_data = (
            "id,name",
            f"{saved_filters[0].pk},Saved Filter 7",
            f"{saved_filters[1].pk},Saved Filter 8",
            f"{saved_filters[2].pk},Saved Filter 9",
        )

        cls.bulk_edit_form_data = {
            "weight": 999,
        }


class TableConfigTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = TableConfig
    # Selected columns are POSTed as a list but compared as a CSV string
    validation_excluded_fields = ("columns", "ordering")

    @classmethod
    def setUpTestData(cls):
        tag_type = ObjectType.objects.get_for_model(Tag)

        users = (
            Tenant(name="Tenant 1", slug="tenant-1"),
            Tenant(name="Tenant 2", slug="tenant-2"),
            Tenant(name="Tenant 3", slug="tenant-3"),
        )
        for user in users:
            user.save()

        table_configs = (
            TableConfig(
                name="Table Config 1",
                object_type=tag_type,
                table="TagTable",
                user=None,
                columns=["name", "slug"],
            ),
            TableConfig(
                name="Table Config 2",
                object_type=tag_type,
                table="TagTable",
                user=None,
                columns=["name", "weight"],
            ),
            TableConfig(
                name="Table Config 3",
                object_type=tag_type,
                table="TagTable",
                user=None,
                columns=["name", "color"],
            ),
        )
        TableConfig.objects.bulk_create(table_configs)

        cls.form_data = {
            "name": "Table Config X",
            "object_type": tag_type.pk,
            "table": "TagTable",
            "description": "A table config",
            "weight": 100,
            "enabled": True,
            "shared": True,
            "columns": ["name", "slug"],
            "ordering": ["name"],
        }
        cls.bulk_edit_form_data = {
            "weight": 999,
        }

    def _get_url(self, action, instance=None):
        url = super()._get_url(action, instance)
        # The add view requires the table context from the source table view
        if action == "add":
            tag_type = ObjectType.objects.get_for_model(Tag)
            url = f"{url}?object_type={tag_type.pk}&table=TagTable"
        return url

    def test_add_view_without_table_context(self):
        """A GET without the table context params must redirect to the home page."""
        self.add_permissions("core.add_tableconfig")
        response = self.client.get(reverse("core:tableconfig_add"))
        self.assertRedirects(response, reverse("home"))

        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            "Table configurations must be created from an object list view.",
        )

    def test_add_view_post_without_table_context(self):
        """A POST without the table context must return form errors rather than a server error."""
        self.add_permissions("core.add_tableconfig")
        response = self.client.post(reverse("core:tableconfig_add"), data={})
        self.assertHttpStatus(response, 200)
