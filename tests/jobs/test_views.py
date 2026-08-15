# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import uuid
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from coldfront.core.choices import JobStatusChoices
from coldfront.core.models import Job, ObjectType
from coldfront.users.models import ObjectPermission
from coldfront.utils.testing import TestCase
from coldfront.utils.testing.utils import disable_warnings


class JobListViewTestCase(TestCase):
    """Test the Job list view."""

    model = Job

    @classmethod
    def setUpTestData(cls):
        cls.jobs = (
            Job.objects.create(
                name="Test Job 1",
                job_id=uuid.uuid4(),
                status=JobStatusChoices.STATUS_COMPLETED,
            ),
            Job.objects.create(
                name="Test Job 2",
                job_id=uuid.uuid4(),
                status=JobStatusChoices.STATUS_RUNNING,
            ),
            Job.objects.create(
                name="Test Job 3",
                job_id=uuid.uuid4(),
                status=JobStatusChoices.STATUS_FAILED,
            ),
        )

    def _get_url(self, action="list", instance=None):
        url_format = "{}:{}_{{}}".format(self.model._meta.app_label, self.model._meta.model_name)
        if instance is None:
            from django.urls import reverse

            return reverse(url_format.format(action))
        from django.urls import reverse

        return reverse(url_format.format(action), kwargs={"pk": instance.pk})

    def test_list_objects_anonymous(self):
        self.client.logout()
        ct = ContentType.objects.get_for_model(self.model)
        if (ct.app_label, ct.model) in settings.EXEMPT_EXCLUDE_MODELS:
            with disable_warnings("django.request"):
                response = self.client.get(self._get_url())
                self.assertHttpStatus(response, 302)

    def test_list_objects_without_permission(self):
        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.get(self._get_url()), 403)

    def test_list_objects_with_permission(self):
        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        self.assertHttpStatus(self.client.get(self._get_url()), 200)

    def test_list_objects_with_constrained_permission(self):
        instance1, instance2 = self.jobs[0], self.jobs[1]

        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.pk}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        response = self.client.get(self._get_url())
        self.assertHttpStatus(response, 200)
        content = str(response.content)
        self.assertIn(instance1.get_absolute_url(), content)
        self.assertNotIn(instance2.get_absolute_url(), content)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_export_objects(self):
        url = self._get_url()

        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        response = self.client.get(f"{url}?export")
        self.assertHttpStatus(response, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv; charset=utf-8")

        response = self.client.get(f"{url}?export=table")
        self.assertHttpStatus(response, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv; charset=utf-8")


class JobDetailViewTestCase(TestCase):
    """Test the Job detail view."""

    model = Job

    @classmethod
    def setUpTestData(cls):
        cls.job = Job.objects.create(
            name="Test Detail Job",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_COMPLETED,
        )

    def _get_url(self, action="", instance=None):
        url_format = "{}:{}_{{}}".format(self.model._meta.app_label, self.model._meta.model_name)
        if instance is None:
            instance = self.job
        from django.urls import reverse

        return reverse(url_format.format(action), kwargs={"pk": instance.pk})

    def test_get_object_anonymous(self):
        self.client.logout()
        ct = ContentType.objects.get_for_model(self.model)
        if (ct.app_label, ct.model) in settings.EXEMPT_EXCLUDE_MODELS:
            with disable_warnings("django.request"):
                response = self.client.get(self.job.get_absolute_url())
                self.assertHttpStatus(response, 302)

    def test_get_object_without_permission(self):
        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.get(self.job.get_absolute_url()), 403)

    def test_get_object_with_permission(self):
        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        self.assertHttpStatus(self.client.get(self.job.get_absolute_url()), 200)

    def test_get_object_with_constrained_permission(self):
        job2 = Job.objects.create(
            name="Another Job",
            job_id=uuid.uuid4(),
        )

        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": self.job.pk}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        self.assertHttpStatus(self.client.get(self.job.get_absolute_url()), 200)
        self.assertHttpStatus(self.client.get(job2.get_absolute_url()), 404)


class JobLogViewTestCase(TestCase):
    """Test the Job log view (tab)."""

    model = Job

    @classmethod
    def setUpTestData(cls):
        cls.job = Job.objects.create(
            name="Log Test Job",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_COMPLETED,
            log_entries=[
                {"timestamp": "2026-01-01T00:00:00", "level": "INFO", "message": "Test log entry"},
            ],
        )

    def _get_url(self, action="log", instance=None):
        url_format = "{}:{}_{{}}".format(self.model._meta.app_label, self.model._meta.model_name)
        if instance is None:
            instance = self.job
        from django.urls import reverse

        return reverse(url_format.format(action), kwargs={"pk": instance.pk})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_log_view(self):
        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        response = self.client.get(self._get_url())
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_log_view_contains_entries(self):
        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        response = self.client.get(self._get_url())
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "Test log entry")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_log_view_empty(self):
        job = Job.objects.create(
            name="Empty Log Job",
            job_id=uuid.uuid4(),
            status=JobStatusChoices.STATUS_PENDING,
        )

        response = self.client.get(self._get_url(instance=job))
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "No log entries")


class JobDeleteViewTestCase(TestCase):
    """Test the Job delete view."""

    model = Job

    @classmethod
    def setUpTestData(cls):
        cls.job = Job.objects.create(
            name="Delete Test Job",
            job_id=uuid.uuid4(),
        )

    def _get_url(self, action="delete", instance=None):
        url_format = "{}:{}_{{}}".format(self.model._meta.app_label, self.model._meta.model_name)
        if instance is None:
            instance = self.job
        from django.urls import reverse

        return reverse(url_format.format(action), kwargs={"pk": instance.pk})

    def test_delete_object_without_permission(self):
        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.get(self._get_url()), 403)

        request = {
            "path": self._get_url(),
            "data": {"confirm": True},
        }
        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.post(**request), 403)

    @patch("coldfront.core.models.jobs.django_rq.get_queue")
    def test_delete_object_with_permission(self, mock_get_queue):
        mock_queue = MagicMock()
        mock_queue.fetch_job.return_value = MagicMock()
        mock_get_queue.return_value = mock_queue

        obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        self.assertHttpStatus(self.client.get(self._get_url()), 200)

        request = {
            "path": self._get_url(),
            "data": {"confirm": True},
        }
        self.assertHttpStatus(self.client.post(**request), 302)

        with self.assertRaises(Job.DoesNotExist):
            self.job.refresh_from_db()

    @patch("coldfront.core.models.jobs.django_rq.get_queue")
    def test_delete_object_with_constrained_permission(self, mock_get_queue):
        mock_queue = MagicMock()
        mock_queue.fetch_job.return_value = MagicMock()
        mock_get_queue.return_value = mock_queue

        job2 = Job.objects.create(
            name="Another Delete Job",
            job_id=uuid.uuid4(),
        )

        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": self.job.pk}, actions=["delete"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        self.assertHttpStatus(self.client.get(self._get_url(instance=self.job)), 200)
        self.assertHttpStatus(self.client.get(self._get_url(instance=job2)), 404)

        request = {
            "path": self._get_url(instance=self.job),
            "data": {"confirm": True},
        }
        self.assertHttpStatus(self.client.post(**request), 302)

        request = {
            "path": self._get_url(instance=job2),
            "data": {"confirm": True},
        }
        self.assertHttpStatus(self.client.post(**request), 404)
