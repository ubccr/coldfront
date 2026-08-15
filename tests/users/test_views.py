# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from coldfront.core.models import ObjectType
from coldfront.users.models import Group, ObjectPermission, Token, User
from coldfront.utils.testing import ViewTestCases


class UserTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = User
    maxDiff = None
    validation_excluded_fields = ["password"]

    def _get_queryset(self):
        # Omit the user attached to the test client
        return self.model.objects.exclude(username="testuser")

    @classmethod
    def setUpTestData(cls):
        group = Group.objects.create(name="Test Group")
        users = (
            User(
                username="username1", first_name="first1", last_name="last1", email="user1@foo.com", password="pass1xxx"
            ),
            User(
                username="username2", first_name="first2", last_name="last2", email="user2@foo.com", password="pass2xxx"
            ),
            User(
                username="username3", first_name="first3", last_name="last3", email="user3@foo.com", password="pass3xxx"
            ),
        )
        User.objects.bulk_create(users)
        cls.group = group

        cls.form_data = {
            "username": "usernamex",
            "first_name": "firstx",
            "last_name": "lastx",
            "email": "userx@foo.com",
            "password": "pass1xxxABCD",
            "confirm_password": "pass1xxxABCD",
        }

        cls.csv_data = (
            "username,first_name,last_name,email,password",
            "username4,first4,last4,email4@foo.com,pass4xxx",
            "username5,first5,last5,email5@foo.com,pass5xxx",
            "username6,first6,last6,email6@foo.com,pass6xxx",
        )

        cls.csv_update_data = (
            "id,first_name,last_name",
            f"{users[0].pk},first7,last7",
            f"{users[1].pk},first8,last8",
            f"{users[2].pk},first9,last9",
        )

        cls.bulk_edit_form_data = {
            "last_name": "newlastname",
            "add_groups": [cls.group.pk],
        }

    def test_password_validation_enforced(self):
        """
        Test that any configured password validation rules (AUTH_PASSWORD_VALIDATORS) are enforced.
        """
        self.add_permissions("users.add_user")
        data = {
            "username": "new_user",
            "password": "F1a",
            "confirm_password": "F1a",
        }

        # Password too short
        request = {
            "path": self._get_url("add"),
            "data": data,
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 200)

        # Password long enough
        data["password"] = "fooBarFoo123"
        data["confirm_password"] = "fooBarFoo123"
        self.assertHttpStatus(self.client.post(**request), 302)

        # Password no letter
        data["password"] = "123456789123"
        data["confirm_password"] = "123456789123"
        self.assertHttpStatus(self.client.post(**request), 200)


class GroupTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
):
    model = Group
    maxDiff = None

    @classmethod
    def setUpTestData(cls):

        groups = (
            Group(name="group1"),
            Group(name="group2"),
            Group(name="group3"),
        )
        Group.objects.bulk_create(groups)

        cls.form_data = {
            "name": "groupx",
        }

        cls.csv_data = (
            "name",
            "group4",
            "group5",
            "group6",
        )

        cls.csv_update_data = (
            "id,name",
            f"{groups[0].pk},group7",
            f"{groups[1].pk},group8",
            f"{groups[2].pk},group9",
        )

        cls.bulk_edit_form_data = {
            "description": "New description",
        }


class ObjectPermissionTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = ObjectPermission
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        object_type = ObjectType.objects.get_by_natural_key("tenancy", "tenant")

        permissions = (
            ObjectPermission(name="Permission 1", actions=["view", "add", "delete"]),
            ObjectPermission(name="Permission 2", actions=["view", "add", "delete"]),
            ObjectPermission(name="Permission 3", actions=["view", "add", "delete"]),
        )
        ObjectPermission.objects.bulk_create(permissions)

        cls.form_data = {
            "name": "Permission X",
            "description": "A new permission",
            "object_types": [object_type.pk],
            "actions": '["view", "edit", "delete"]',
        }

        cls.bulk_edit_form_data = {
            "description": "New description",
        }


class TokenTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = Token
    maxDiff = None
    validation_excluded_fields = ["token", "user"]

    @classmethod
    def setUpTestData(cls):
        users = (
            User(
                username="username1", first_name="first1", last_name="last1", email="user1@foo.com", password="pass1xxx"
            ),
            User(
                username="username2", first_name="first2", last_name="last2", email="user2@foo.com", password="pass2xxx"
            ),
        )
        User.objects.bulk_create(users)
        tokens = (
            Token(user=users[0]),
            Token(user=users[0]),
            Token(user=users[1]),
        )
        for token in tokens:
            token.save()

        cls.form_data = {
            "token": "4F9DAouzURLbicyoG55htImgqQ0b4UZHP5LUYgl5",
            "user": users[0].pk,
            "description": "Test token",
            "enabled": True,
        }

        cls.csv_data = (
            "token,user,description,enabled,write_enabled",
            f"zjebxBPzICiPbWz0Wtx0fTL7bCKXKGTYhNzkgC2S,{users[0].pk},Test token,true,true",
            f"9Z5kGtQWba60Vm226dPDfEAV6BhlTr7H5hAXAfbF,{users[1].pk},Test token,true,false",
            f"njpMnNT6r0k0MDccoUhTYYlvP9BvV3qLzYN2p6Uu,{users[1].pk},Test token,false,true",
        )

        cls.csv_update_data = (
            "id,description",
            f"{tokens[0].pk},New description",
            f"{tokens[1].pk},New description",
            f"{tokens[2].pk},New description",
        )

        cls.bulk_edit_form_data = {
            "description": "New description",
        }
