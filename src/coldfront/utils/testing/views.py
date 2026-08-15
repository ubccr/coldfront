# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import csv

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ForeignKey
from django.test import override_settings
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext as _

from coldfront.core.choices import CSVDelimiterChoices, ImportFormatChoices, ObjectChangeActionChoices
from coldfront.core.models import ObjectChange, ObjectType
from coldfront.models.features import ChangeLoggingMixin
from coldfront.users.models import ObjectPermission

from .base import ModelTestCase
from .utils import disable_warnings, get_random_string, post_data


class ModelViewTestCase(ModelTestCase):
    """
    Base TestCase for model views. Subclass to test individual views.
    """

    def _get_base_url(self):
        """
        Return the base format for a URL for the test's model. Override this to test for a model which belongs
        to a different app (e.g. testing Interfaces within the virtualization app).
        """
        return "{}:{}_{{}}".format(self.model._meta.app_label, self.model._meta.model_name)

    def _get_url(self, action, instance=None):
        """
        Return the URL name for a specific action and optionally a specific instance
        """
        url_format = self._get_base_url()

        # If no instance was provided, assume we don't need a unique identifier
        if instance is None:
            return reverse(url_format.format(action))

        return reverse(url_format.format(action), kwargs={"pk": instance.pk})


class ViewTestCases:
    """
    We keep any TestCases with test_* methods inside a class to prevent unittest from trying to run them.
    """

    class GetObjectViewTestCase(ModelViewTestCase):
        """
        Retrieve a single instance.
        """

        def test_get_object_anonymous(self):
            # Make the request as an unauthenticated user
            self.client.logout()
            ct = ContentType.objects.get_for_model(self.model)
            if (ct.app_label, ct.model) in settings.EXEMPT_EXCLUDE_MODELS:
                # Models listed in EXEMPT_EXCLUDE_MODELS should not be accessible to anonymous users
                with disable_warnings("django.request"):
                    response = self.client.get(self._get_queryset().first().get_absolute_url())
                    self.assertHttpStatus(response, 302)

        def test_get_object_without_permission(self):
            instance = self._get_queryset().first()

            # Try GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(instance.get_absolute_url()), 403)

        def test_get_object_with_permission(self):
            instance = self._get_queryset().first()

            # Add model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(instance.get_absolute_url()), 200)

        def test_get_object_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET to permitted object
            self.assertHttpStatus(self.client.get(instance1.get_absolute_url()), 200)

            # Try GET to non-permitted object
            self.assertHttpStatus(self.client.get(instance2.get_absolute_url()), 404)

    class GetObjectChangelogViewTestCase(ModelViewTestCase):
        """
        View the changelog for an instance.
        """

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_get_object_changelog(self):
            url = self._get_url("changelog", self._get_queryset().first())
            response = self.client.get(url)
            self.assertHttpStatus(response, 200)

    class CreateObjectViewTestCase(ModelViewTestCase):
        """
        Create a single new instance.

        :form_data: Data to be used when creating a new object.
        """

        form_data = {}
        validation_excluded_fields = []

        def test_create_object_without_permission(self):

            # Try GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("add")), 403)

            # Try POST without permission
            request = {
                "path": self._get_url("add"),
                "data": post_data(self.form_data),
            }
            response = self.client.post(**request)
            with disable_warnings("django.request"):
                self.assertHttpStatus(response, 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_create_object_with_permission(self):
            # Assign unconstrained permission
            obj_perm = ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("add")), 200)

            # Add custom field data if the model supports it
            # if issubclass(self.model, CustomFieldsMixin):
            #    add_custom_field_data(self.form_data, self.model)

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                if "changelog_message" not in self.form_data:
                    self.form_data["changelog_message"] = get_random_string(10)

            # Try POST with model-level permission
            initial_count = self._get_queryset().count()
            request = {
                "path": self._get_url("add"),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertEqual(initial_count + 1, self._get_queryset().count())
            instance = self._get_queryset().order_by("pk").last()
            self.assertInstanceEqual(instance, self.form_data, exclude=self.validation_excluded_fields)

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(instance), changed_object_id=instance.pk
                )

                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_CREATE)
                self.assertEqual(objectchanges[0].message, self.form_data["changelog_message"])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_create_object_with_constrained_permission(self):

            # Assign constrained permission
            obj_perm = ObjectPermission(
                name="Test permission",
                constraints={"pk": 0},  # Dummy permission to deny all
                actions=["add"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with object-level permission
            self.assertHttpStatus(self.client.get(self._get_url("add")), 200)

            # Try to create an object (not permitted)
            initial_count = self._get_queryset().count()
            request = {
                "path": self._get_url("add"),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 200)
            self.assertEqual(initial_count, self._get_queryset().count())  # Check that no object was created

            # Update the ObjectPermission to allow creation
            obj_perm.constraints = {"pk__gt": 0}
            obj_perm.save()

            # Try to create an object (permitted)
            request = {
                "path": self._get_url("add"),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertEqual(initial_count + 1, self._get_queryset().count())
            instance = self._get_queryset().order_by("pk").last()
            self.assertInstanceEqual(instance, self.form_data, exclude=self.validation_excluded_fields)

    class EditObjectViewTestCase(ModelViewTestCase):
        """
        Edit a single existing instance.

        :form_data: Data to be used when updating the first existing object.
        """

        form_data = {}
        validation_excluded_fields = []

        def test_edit_object_without_permission(self):
            instance = self._get_queryset().first()

            # Try GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("edit", instance)), 403)

            # Try POST without permission
            request = {
                "path": self._get_url("edit", instance),
                "data": post_data(self.form_data),
            }
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(**request), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_edit_object_with_permission(self):
            instance = self._get_queryset().first()

            # Assign model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("edit", instance)), 200)

            # Add custom field data if the model supports it
            # if issubclass(self.model, CustomFieldsMixin):
            #    add_custom_field_data(self.form_data, self.model)

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                if "changelog_message" not in self.form_data:
                    self.form_data["changelog_message"] = get_random_string(10)

            # Try POST with model-level permission
            request = {
                "path": self._get_url("edit", instance),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            instance = self._get_queryset().get(pk=instance.pk)
            self.assertInstanceEqual(instance, self.form_data, exclude=self.validation_excluded_fields)

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(instance), changed_object_id=instance.pk
                )
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_UPDATE)
                self.assertEqual(objectchanges[0].message, self.form_data["changelog_message"])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_edit_object_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Assign constrained permission
            obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with a permitted object
            self.assertHttpStatus(self.client.get(self._get_url("edit", instance1)), 200)

            # Try GET with a non-permitted object
            self.assertHttpStatus(self.client.get(self._get_url("edit", instance2)), 404)

            # Try to edit a permitted object
            request = {
                "path": self._get_url("edit", instance1),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            instance = self._get_queryset().get(pk=instance1.pk)
            self.assertInstanceEqual(instance, self.form_data, exclude=self.validation_excluded_fields)

            # Try to edit a non-permitted object
            request = {
                "path": self._get_url("edit", instance2),
                "data": post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 404)

    class DeleteObjectViewTestCase(ModelViewTestCase):
        """
        Delete a single instance.
        """

        def test_delete_object_without_permission(self):
            instance = self._get_queryset().first()

            # Try GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), 403)

            # Try POST without permission
            request = {
                "path": self._get_url("delete", instance),
                "data": post_data({"confirm": True}),
            }
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(**request), 403)

        def test_delete_object_with_permission(self):
            instance = self._get_queryset().last()
            form_data = {"confirm": True}

            # Assign model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), 200)

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                form_data["changelog_message"] = get_random_string(10)

            # Try POST with model-level permission
            request = {
                "path": self._get_url("delete", instance),
                "data": post_data(form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            with self.assertRaises(ObjectDoesNotExist):
                self._get_queryset().get(pk=instance.pk)

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(instance), changed_object_id=instance.pk
                )
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_DELETE)
                self.assertEqual(objectchanges[0].message, form_data["changelog_message"])

        def test_delete_object_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Assign object-level permission
            obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with a permitted object
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance1)), 200)

            # Try GET with a non-permitted object
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance2)), 404)

            # Try to delete a permitted object
            request = {
                "path": self._get_url("delete", instance1),
                "data": post_data({"confirm": True}),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            with self.assertRaises(ObjectDoesNotExist):
                self._get_queryset().get(pk=instance1.pk)

            # Try to delete a non-permitted object
            request = {
                "path": self._get_url("delete", instance2),
                "data": post_data({"confirm": True}),
            }
            self.assertHttpStatus(self.client.post(**request), 404)
            self.assertTrue(self._get_queryset().filter(pk=instance2.pk).exists())

    class ListObjectsViewTestCase(ModelViewTestCase):
        """
        Retrieve multiple instances.
        """

        def test_list_objects_anonymous(self):
            # Make the request as an unauthenticated user
            self.client.logout()
            ct = ContentType.objects.get_for_model(self.model)
            if (ct.app_label, ct.model) in settings.EXEMPT_EXCLUDE_MODELS:
                # Models listed in EXEMPT_EXCLUDE_MODELS should not be accessible to anonymous users
                with disable_warnings("django.request"):
                    response = self.client.get(self._get_url("list"))
                    self.assertHttpStatus(response, 302)

        def test_list_objects_without_permission(self):

            # Try GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("list")), 403)

        def test_list_objects_with_permission(self):

            # Add model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("list")), 200)

        def test_list_objects_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with object-level permission
            response = self.client.get(self._get_url("list"))
            self.assertHttpStatus(response, 200)
            content = str(response.content)
            self.assertIn(instance1.get_absolute_url(), content)
            self.assertNotIn(instance2.get_absolute_url(), content)

        def test_export_objects(self):
            url = self._get_url("list")

            # Add model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Test default CSV export
            response = self.client.get(f"{url}?export")
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.get("Content-Type"), "text/csv; charset=utf-8")

            # Test table-based export
            response = self.client.get(f"{url}?export=table")
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.get("Content-Type"), "text/csv; charset=utf-8")

    class BulkImportObjectsViewTestCase(ModelViewTestCase):
        """
        Create multiple instances from imported data.

        :csv_data: CSV data for bulk import testing. Supports two formats:

            1. Tuple/list format (backwards compatible):
                csv_data = (
                    "name,slug,description",
                    "Object 1,object-1,First object",
                    "Object 2,object-2,Second object",
                )

            2. Dictionary format for multiple scenarios:
                csv_data = {
                    'default': (
                        "name,slug,description",
                        "Object 1,object-1,First object",
                    ),
                    'with_optional_fields': (
                        "name,slug,description,comments",
                        "Object 2,object-2,Second object,With comments",
                    )
                }

            When using dictionary format, test_bulk_import_objects_with_permission()
            runs each scenario as a separate subtest with clear output:

                test_bulk_import_objects_with_permission (scenario=default) ... ok
                test_bulk_import_objects_with_permission (scenario=with_optional_fields) ... ok
        """

        csv_data = ()

        def get_scenarios(self):
            return self.csv_data.keys() if isinstance(self.csv_data, dict) else ["default"]

        def _get_csv_data(self, scenario_name="default"):
            """
            Get CSV data for testing. Supports both tuple/list and dictionary formats.
            """
            if isinstance(self.csv_data, dict):
                if scenario_name not in self.csv_data:
                    available = ", ".join(self.csv_data.keys())
                    raise ValueError(f"Scenario '{scenario_name}' not found in csv_data. Available: {available}")
                return "\n".join(self.csv_data[scenario_name])
            if isinstance(self.csv_data, (tuple, list)):
                return "\n".join(self.csv_data)
            raise TypeError(f"csv_data must be a tuple, list, or dictionary, got {type(self.csv_data)}")

        def _get_update_csv_data(self):
            return self.csv_update_data, "\n".join(self.csv_update_data)

        def test_bulk_import_objects_without_permission(self):
            data = {
                "data": self._get_csv_data(),
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.AUTO,
            }

            # Test GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("bulk_import")), 403)

            # Try POST without permission
            response = self.client.post(self._get_url("bulk_import"), data)
            with disable_warnings("django.request"):
                self.assertHttpStatus(response, 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_bulk_import_objects_with_permission(self, post_import_callback=None):
            # Assign model-level permission once for all scenarios
            obj_perm = ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission (only once)
            self.assertHttpStatus(self.client.get(self._get_url("bulk_import")), 200)

            # Test each scenario
            for scenario_name in self.get_scenarios():
                with self.cleanupSubTest(scenario=scenario_name):
                    self._test_bulk_import_with_permission_scenario(scenario_name)

                    if post_import_callback:
                        post_import_callback(scenario_name)

        def _test_bulk_import_with_permission_scenario(self, scenario_name):
            """
            Helper method to test a single bulk import scenario.
            """
            initial_count = self._get_queryset().count()

            # Get CSV data for this scenario
            scenario_data = self._get_csv_data(scenario_name)
            expected_new_objects = len(scenario_data.splitlines()) - 1

            data = {
                "data": scenario_data,
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.AUTO,
            }

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                data["changelog_message"] = get_random_string(10)

            # Test POST with permission
            response = self.client.post(self._get_url("bulk_import"), data)
            self.assertHttpStatus(response, 302)

            # Verify object count increase
            self.assertEqual(self._get_queryset().count(), initial_count + expected_new_objects)

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                request_id = response.headers.get("X-Request-ID")
                self.assertIsNotNone(request_id, "Unable to determine request ID from response")
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(self.model),
                    request_id=request_id,
                    action=ObjectChangeActionChoices.ACTION_CREATE,
                )
                self.assertEqual(len(objectchanges), expected_new_objects)

                for oc in objectchanges:
                    self.assertEqual(oc.message, data["changelog_message"])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_update_objects_with_permission(self):
            if not hasattr(self, "csv_update_data"):
                raise NotImplementedError(_("The test must define csv_update_data."))

            initial_count = self._get_queryset().count()
            array, csv_data = self._get_update_csv_data()
            data = {
                "format": ImportFormatChoices.CSV,
                "data": csv_data,
                "csv_delimiter": CSVDelimiterChoices.AUTO,
            }

            # Assign model-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Test POST with permission
            self.assertHttpStatus(self.client.post(self._get_url("bulk_import"), data), 302)
            self.assertEqual(initial_count, self._get_queryset().count())

            reader = csv.DictReader(array, delimiter=",")
            check_data = list(reader)
            for line in check_data:
                obj = self.model.objects.get(id=line["id"])
                for attr, value in line.items():
                    if attr != "id":
                        field = self.model._meta.get_field(attr)
                        value = getattr(obj, attr)
                        # cannot verify FK fields as don't know what name the CSV maps to
                        if value is not None and not isinstance(field, ForeignKey):
                            self.assertEqual(value, value)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_bulk_import_objects_with_constrained_permission(self, post_import_callback=None):
            # Assign constrained permission (deny all initially)
            obj_perm = ObjectPermission(
                name="Test permission",
                constraints={"pk": 0},  # Dummy permission to deny all
                actions=["add"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Test each scenario with constrained permissions
            for scenario_name in self.get_scenarios():
                with self.cleanupSubTest(scenario=scenario_name):
                    self._test_bulk_import_constrained_scenario(scenario_name, obj_perm)

                    if post_import_callback:
                        post_import_callback(scenario_name)

        def _test_bulk_import_constrained_scenario(self, scenario_name, obj_perm):
            """
            Helper method to test a single bulk import scenario with constrained permissions.
            """
            initial_count = self._get_queryset().count()

            # Get CSV data for this scenario
            scenario_data = self._get_csv_data(scenario_name)
            expected_new_objects = len(scenario_data.splitlines()) - 1

            data = {
                "data": scenario_data,
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.AUTO,
            }

            # Attempt to import non-permitted objects (should fail)
            self.assertHttpStatus(self.client.post(self._get_url("bulk_import"), data), 200)
            self.assertEqual(self._get_queryset().count(), initial_count)

            # Update permission constraints to allow all
            obj_perm.constraints = {"pk__gt": 0}  # Dummy permission to allow all
            obj_perm.save()

            # Import permitted objects (should succeed)
            self.assertHttpStatus(self.client.post(self._get_url("bulk_import"), data), 302)
            self.assertEqual(self._get_queryset().count(), initial_count + expected_new_objects)

    class BulkEditObjectsViewTestCase(ModelViewTestCase):
        """
        Edit multiple instances.

        Note: Tests are conditional on the model having a ``bulk_edit`` URL pattern
        registered. If the URL pattern doesn't exist, the tests are skipped.

        The test uses ``bulk_edit_form_data`` for form values. Subclasses must define
        ``cls.bulk_edit_form_data`` to provide the fields to change during bulk edit.
        """

        bulk_edit_form_data = {}

        def _bulk_edit_url_exists(self):
            """
            Check whether the bulk_edit URL pattern is registered for this model.
            Returns True if the URL resolves, False otherwise.
            """
            try:
                self._get_url("bulk_edit")
                return True
            except NoReverseMatch:
                return False

        def test_bulk_edit_objects_without_permission(self):
            if not self._bulk_edit_url_exists():
                self.skipTest("bulk_edit URL not registered for this model")

            pk_list = self._get_queryset().values_list("pk", flat=True)[:3]
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }

            # Test GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("bulk_edit")), 403)

            # Try POST without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(self._get_url("bulk_edit"), data), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_bulk_edit_objects_with_permission(self):
            if not self._bulk_edit_url_exists():
                self.skipTest("bulk_edit URL not registered for this model")

            pk_list = list(self._get_queryset().values_list("pk", flat=True))[:3]
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }

            # Merge bulk_edit_form_data into data
            data.update(self.bulk_edit_form_data)

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                if "changelog_message" not in data:
                    data["changelog_message"] = get_random_string(10)

            # Assign unconstrained permission
            obj_perm = ObjectPermission(name="Test permission", actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("bulk_edit")), 302)  # GET redirects to return_url

            # Try POST with model-level permission
            response = self.client.post(self._get_url("bulk_edit"), data)
            self.assertHttpStatus(response, 302)

            # Verify objects were updated
            for pk in pk_list:
                instance = self._get_queryset().get(pk=pk)
                self.assertInstanceEqual(instance, self.bulk_edit_form_data)

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(self.model),
                    changed_object_id__in=pk_list,
                )
                self.assertEqual(len(objectchanges), len(pk_list))
                for oc in objectchanges:
                    self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
                    self.assertEqual(oc.message, data["changelog_message"])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
        def test_bulk_edit_objects_with_constrained_permission(self):
            if not self._bulk_edit_url_exists():
                self.skipTest("bulk_edit URL not registered for this model")

            pk_list = self._get_queryset().values_list("pk", flat=True)[:3]
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }

            # Merge bulk_edit_form_data into data
            data.update(self.bulk_edit_form_data)

            # Dynamically determine a constraint that will *not* be matched by the updated objects.
            attr_name = list(self.bulk_edit_form_data.keys())[0]
            field = self.model._meta.get_field(attr_name)
            value = field.value_from_object(self._get_queryset().first())

            # Assign constrained permission
            obj_perm = ObjectPermission(
                name="Test permission",
                constraints={attr_name: value},
                actions=["change"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Attempt to bulk edit permitted objects into a non-permitted state (should get form validation error)
            self.assertHttpStatus(self.client.post(self._get_url("bulk_edit"), data), 200)

            # Update permission constraints
            obj_perm.constraints = {"pk__gt": 0}
            obj_perm.save()

            # Bulk edit permitted objects (should succeed)
            self.assertHttpStatus(self.client.post(self._get_url("bulk_edit"), data), 302)

            # Verify objects were updated
            for pk in pk_list:
                instance = self._get_queryset().get(pk=pk)
                self.assertInstanceEqual(instance, self.bulk_edit_form_data)

    class BulkDeleteObjectsViewTestCase(ModelViewTestCase):
        """
        Delete multiple instances.
        """

        def test_bulk_delete_objects_without_permission(self):
            pk_list = self._get_queryset().values_list("pk", flat=True)[:3]
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # Test GET without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("bulk_delete")), 403)

            # Try POST without permission
            with disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(self._get_url("bulk_delete"), data), 403)

        def test_bulk_delete_objects_with_permission(self):
            pk_list = list(self._get_queryset().values_list("pk", flat=True))[:3]
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # If supported, add a changelog message
            if issubclass(self.model, ChangeLoggingMixin):
                data["changelog_message"] = get_random_string(10)

            # Assign unconstrained permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Try POST with model-level permission
            response = self.client.post(self._get_url("bulk_delete"), data)
            self.assertHttpStatus(response, 302)
            self.assertFalse(self._get_queryset().filter(pk__in=pk_list).exists())

            # Verify ObjectChange creation
            if issubclass(self.model, ChangeLoggingMixin):
                objectchanges = ObjectChange.objects.filter(
                    changed_object_type=ContentType.objects.get_for_model(self.model), changed_object_id__in=pk_list
                )
                self.assertEqual(len(objectchanges), len(pk_list))
                for oc in objectchanges:
                    self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
                    self.assertEqual(oc.message, data["changelog_message"])

        def test_bulk_delete_objects_with_constrained_permission(self):
            pk_list = self._get_queryset().values_list("pk", flat=True)
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # Assign constrained permission
            obj_perm = ObjectPermission(
                name="Test permission",
                constraints={"pk": 0},  # Dummy permission to deny all
                actions=["delete"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

            # Attempt to bulk delete non-permitted objects
            initial_count = self._get_queryset().count()
            self.assertHttpStatus(self.client.post(self._get_url("bulk_delete"), data), 302)
            self.assertEqual(self._get_queryset().count(), initial_count)

            # Update permission constraints
            obj_perm.constraints = {"pk__gt": 0}  # Dummy permission to allow all
            obj_perm.save()

            # Bulk delete permitted objects
            self.assertHttpStatus(self.client.post(self._get_url("bulk_delete"), data), 302)
            self.assertEqual(self._get_queryset().count(), 0)

    class PrimaryObjectViewTestCase(
        GetObjectViewTestCase,
        GetObjectChangelogViewTestCase,
        CreateObjectViewTestCase,
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        ListObjectsViewTestCase,
        BulkImportObjectsViewTestCase,
        BulkEditObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for all primary objects
        """

        pass

    class OrganizationalObjectViewTestCase(
        GetObjectViewTestCase,
        GetObjectChangelogViewTestCase,
        CreateObjectViewTestCase,
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        ListObjectsViewTestCase,
        BulkImportObjectsViewTestCase,
        BulkEditObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for all organizational objects
        """

        pass
