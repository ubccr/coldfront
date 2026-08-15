# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import datetime

from django.conf import settings
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from coldfront.core.models import ObjectType
from coldfront.ras.models import Project
from coldfront.tenancy.models import Tenant
from coldfront.users.constants import TOKEN_PREFIX
from coldfront.users.models import Group, ObjectPermission, Token, User
from coldfront.utils.testing import APITestCase, TestCase


class TokenAuthenticationTestCase(APITestCase):
    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_no_token(self):
        # Request without a token should return a 403
        response = self.client.get(reverse("ras-api:project-list"))
        self.assertEqual(response.status_code, 403)

    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_token_valid(self):
        # Create a token
        token = Token.objects.create(user=self.user)

        # Valid token should return a 200
        header = f"Bearer {TOKEN_PREFIX}{token.key}.{token.token}"
        response = self.client.get(reverse("ras-api:project-list"), headers={"authorization": header})
        self.assertEqual(response.status_code, 200, response.data)

        # Check that the token's last_used time has been updated
        token.refresh_from_db()
        self.assertIsNotNone(token.last_used)

    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_token_invalid(self):
        # Invalid token should return a 403
        header = f"Bearer {TOKEN_PREFIX}XXXXXX.XXXXXXXXXX"
        response = self.client.get(reverse("tenancy-api:tenant-list"), headers={"authorization": header})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Invalid token")

    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_token_enabled(self):
        url = reverse("ras-api:project-list")

        # Create tokens
        token = Token.objects.create(user=self.user, enabled=True)

        # Request with an enabled token should succeed
        response = self.client.get(url, headers={"authorization": f"Bearer {TOKEN_PREFIX}{token.key}.{token.token}"})
        self.assertEqual(response.status_code, 200)

        # Request with a disabled token should fail
        token.enabled = False
        token.save()
        response = self.client.get(url, headers={"authorization": f"Bearer {TOKEN_PREFIX}{token.key}.{token.token}"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Token disabled")

    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_token_expiration(self):
        url = reverse("ras-api:project-list")

        # Create token
        future = datetime.datetime(2100, 1, 1, tzinfo=datetime.UTC)
        token = Token.objects.create(user=self.user, expires=future)

        # Request with a non-expired token should succeed
        response = self.client.get(url, headers={"authorization": f"Bearer {TOKEN_PREFIX}{token.key}.{token.token}"})
        self.assertEqual(response.status_code, 200)

        # Request with an expired token should fail
        past = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
        token.expires = past
        token.save()
        response = self.client.get(url, headers={"authorization": f"Bearer {TOKEN_PREFIX}{token.key}"})
        self.assertEqual(response.status_code, 403)

    @override_settings(LOGIN_REQUIRED=True, EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_token_write_enabled(self):
        url = reverse("tenancy-api:tenant-list")
        data = [
            {
                "name": "Tenant 1",
                "slug": "tenant-1",
            },
            {
                "name": "Tenant 2",
                "slug": "tenant-2",
            },
        ]
        self.add_permissions("tenancy.view_tenant", "tenancy.add_tenant")

        # Create tokens
        token = Token.objects.create(user=self.user, write_enabled=False)
        token_header = f"Bearer {TOKEN_PREFIX}{token.key}.{token.token}"

        # GET request with a write-disabled token should succeed
        response = self.client.get(url, headers={"authorization": token_header})
        self.assertEqual(response.status_code, 200)

        # POST request with a write-disabled token should fail
        response = self.client.post(url, data[1], format="json", headers={"authorization": token_header})
        self.assertEqual(response.status_code, 403)

        # POST request with a write-enabled token should succeed
        token.write_enabled = True
        token.save()
        response = self.client.post(url, data[1], format="json", headers={"authorization": token_header})
        self.assertEqual(response.status_code, 201)


class ExternalAuthenticationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="remoteuser1")

    def setUp(self):
        self.client = Client()

    @override_settings(LOGIN_REQUIRED=True)
    def test_remote_auth_disabled(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser1",
        }

        self.assertFalse(settings.REMOTE_AUTH_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        # Client should not be authenticated
        self.client.get(reverse("home"), follow=True, **headers)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(REMOTE_AUTH_ENABLED=True, LOGIN_REQUIRED=True)
    def test_remote_auth_enabled(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser1",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.pk, msg="Authentication failed")

    @override_settings(REMOTE_AUTH_ENABLED=True, REMOTE_AUTH_HEADER="HTTP_FOO", LOGIN_REQUIRED=True)
    def test_remote_auth_custom_header(self):
        """
        Test enabling remote authentication with a custom HTTP header.
        """
        headers = {
            "HTTP_FOO": "remoteuser1",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_FOO")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.pk, msg="Authentication failed")

    @override_settings(REMOTE_AUTH_ENABLED=True, LOGIN_REQUIRED=True)
    def test_remote_auth_user_profile(self):
        """
        Test remote authentication with user profile details.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser1",
            "HTTP_REMOTE_USER_FIRST_NAME": "John",
            "HTTP_REMOTE_USER_LAST_NAME": "Smith",
            "HTTP_REMOTE_USER_EMAIL": "johnsmith@example.com",
        }

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        self.user = User.objects.get(username="remoteuser1")
        self.assertEqual(self.user.first_name, "John", msg="User first name was not updated")
        self.assertEqual(self.user.last_name, "Smith", msg="User last name was not updated")
        self.assertEqual(self.user.email, "johnsmith@example.com", msg="User email was not updated")

    @override_settings(REMOTE_AUTH_ENABLED=True, REMOTE_AUTH_AUTO_CREATE_USER=True, LOGIN_REQUIRED=True)
    def test_remote_auth_auto_create(self):
        """
        Test enabling remote authentication with automatic user creation disabled.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        # Local user should have been automatically created
        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), new_user.pk, msg="Authentication failed")

    @override_settings(
        REMOTE_AUTH_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        REMOTE_AUTH_DEFAULT_GROUPS=["Group 1", "Group 2"],
        LOGIN_REQUIRED=True,
    )
    def test_remote_auth_default_groups(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(settings.REMOTE_AUTH_DEFAULT_GROUPS, ["Group 1", "Group 2"])

        # Create required groups
        groups = (
            Group(name="Group 1"),
            Group(name="Group 2"),
            Group(name="Group 3"),
        )
        Group.objects.bulk_create(groups)

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), new_user.pk, msg="Authentication failed")
        self.assertListEqual([groups[0], groups[1]], list(new_user.groups.all()))

    @override_settings(
        REMOTE_AUTH_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        REMOTE_AUTH_DEFAULT_PERMISSIONS={"ras.add_project": None, "ras.change_project": None},
        LOGIN_REQUIRED=True,
    )
    def test_remote_auth_default_permissions(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(
            settings.REMOTE_AUTH_DEFAULT_PERMISSIONS, {"ras.add_project": None, "ras.change_project": None}
        )

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), new_user.pk, msg="Authentication failed")
        self.assertTrue(new_user.has_perms(["ras.add_project", "ras.change_project"]))

    @override_settings(
        REMOTE_AUTH_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        REMOTE_AUTH_GROUP_SYNC_ENABLED=True,
        LOGIN_REQUIRED=True,
    )
    def test_remote_auth_remote_groups_default(self):
        """
        Test enabling remote authentication with group sync enabled with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
            "HTTP_REMOTE_USER_GROUP": "Group 1|Group 2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertTrue(settings.REMOTE_AUTH_GROUP_SYNC_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_HEADER, "HTTP_REMOTE_USER_GROUP")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_SEPARATOR, "|")

        # Create required groups
        groups = (
            Group(name="Group 1"),
            Group(name="Group 2"),
            Group(name="Group 3"),
        )
        Group.objects.bulk_create(groups)

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), new_user.pk, msg="Authentication failed")
        self.assertListEqual([groups[0], groups[1]], list(new_user.groups.all()))

    @override_settings(
        REMOTE_AUTH_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        REMOTE_AUTH_GROUP_SYNC_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_GROUPS=True,
        LOGIN_REQUIRED=True,
    )
    def test_remote_auth_remote_groups_autocreate(self):
        """
        Test enabling remote authentication with group sync and autocreate
        enabled with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
            "HTTP_REMOTE_USER_GROUP": "Group 1|Group 2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_GROUPS)
        self.assertTrue(settings.REMOTE_AUTH_GROUP_SYNC_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_HEADER, "HTTP_REMOTE_USER_GROUP")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_SEPARATOR, "|")

        groups = (
            Group(name="Group 1"),
            Group(name="Group 2"),
        )

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(
            int(self.client.session.get("_auth_user_id")),
            new_user.pk,
            msg="Authentication failed",
        )
        self.assertListEqual(
            [group.name for group in groups],
            [group.name for group in list(new_user.groups.all())],
        )

    @override_settings(
        REMOTE_AUTH_ENABLED=True,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        REMOTE_AUTH_GROUP_SYNC_ENABLED=True,
        REMOTE_AUTH_HEADER="HTTP_FOO",
        REMOTE_AUTH_GROUP_HEADER="HTTP_BAR",
        LOGIN_REQUIRED=True,
    )
    def test_remote_auth_remote_groups_custom_header(self):
        """
        Test enabling remote authentication with group sync enabled with the default configuration.
        """
        headers = {
            "HTTP_FOO": "remoteuser2",
            "HTTP_BAR": "Group 1|Group 2",
        }

        self.assertTrue(settings.REMOTE_AUTH_ENABLED)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertTrue(settings.REMOTE_AUTH_GROUP_SYNC_ENABLED)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_FOO")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_HEADER, "HTTP_BAR")
        self.assertEqual(settings.REMOTE_AUTH_GROUP_SEPARATOR, "|")

        # Create required groups
        groups = (
            Group(name="Group 1"),
            Group(name="Group 2"),
            Group(name="Group 3"),
        )
        Group.objects.bulk_create(groups)

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), new_user.pk, msg="Authentication failed")
        self.assertListEqual([groups[0], groups[1]], list(new_user.groups.all()))


class ObjectPermissionAPIViewTestCase(TestCase):
    client_class = APIClient

    @classmethod
    def setUpTestData(cls):

        cls.users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        for user in cls.users:
            user.save()

        cls.tenants = (
            Tenant(name="Tenant 1", slug="tenant-1"),
            Tenant(name="Tenant 2", slug="tenant-2"),
            Tenant(name="Tenant 3", slug="tenant-3"),
        )
        Tenant.objects.bulk_create(cls.tenants)

        cls.projects = (
            Project(name="Project 1", tenant=cls.tenants[0], owner=cls.users[0]),
            Project(name="Project 2", tenant=cls.tenants[0], owner=cls.users[0]),
            Project(name="Project 3", tenant=cls.tenants[0], owner=cls.users[0]),
            Project(name="Project 4", tenant=cls.tenants[1], owner=cls.users[1]),
            Project(name="Project 5", tenant=cls.tenants[1], owner=cls.users[1]),
            Project(name="Project 6", tenant=cls.tenants[1], owner=cls.users[1]),
            Project(name="Project 7", tenant=cls.tenants[2], owner=cls.users[2]),
            Project(name="Project 8", tenant=cls.tenants[2], owner=cls.users[2]),
            Project(name="Project 9", tenant=cls.tenants[2], owner=cls.users[2]),
        )
        Project.objects.bulk_create(cls.projects)

    def setUp(self):
        """
        Create a test user and token for API calls.
        """
        self.user = User.objects.create(username="testuser")
        self.token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN_PREFIX}{self.token.key}.{self.token.token}"}

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object(self):

        # Attempt to retrieve object without permission
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission(name="Test permission", constraints={"tenant__name": "Tenant 1"}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(Project))

        # Retrieve permitted object
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)

        # Attempt to retrieve non-permitted object
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[3].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 404)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_objects(self):
        url = reverse("ras-api:project-list")

        # Attempt to list objects without permission
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission(name="Test permission", constraints={"tenant__name": "Tenant 1"}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(Project))

        # Retrieve all objects. Only permitted objects should be returned.
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_create_object(self):
        url = reverse("ras-api:project-list")
        data = {
            "name": "Project 10",
            "tenant": self.tenants[1].pk,
            "owner": self.users[1].pk,
        }
        initial_count = Project.objects.count()

        # Attempt to create an object without permission
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission(name="Test permission", constraints={"tenant__name": "Tenant 1"}, actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(Project))

        # Attempt to create a non-permitted object
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Project.objects.count(), initial_count)

        # Create a permitted object
        data["tenant"] = self.tenants[0].pk
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Project.objects.count(), initial_count + 1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_edit_object(self):

        # Attempt to edit an object without permission
        data = {"tenant": self.tenants[0].pk}
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission(
            name="Test permission", constraints={"tenant__name": "Tenant 1"}, actions=["change"]
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(Project))

        # Attempt to edit a non-permitted object
        data = {"tenant": self.tenants[0].pk}
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[3].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 404)

        # Edit a permitted object
        data["status"] = "archived"
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 200)

        # Attempt to modify a permitted object to a non-permitted object
        data["tenant"] = self.tenants[1].pk
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_delete_object(self):

        # Attempt to delete an object without permission
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission(
            name="Test permission", constraints={"tenant__name": "Tenant 1"}, actions=["delete"]
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(Project))

        # Attempt to delete a non-permitted object
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[3].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 404)

        # Delete a permitted object
        url = reverse("ras-api:project-detail", kwargs={"pk": self.projects[0].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 204)
