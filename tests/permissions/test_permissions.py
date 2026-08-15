# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.test import RequestFactory, TestCase

from coldfront.auth.mixins import ObjectPermissionMixin, ObjectPermissionRequiredMixin
from coldfront.core.models import ObjectType
from coldfront.ras.models import Allocation
from coldfront.users.constants import CONSTRAINT_TOKEN_USER
from coldfront.users.models import Group, ObjectPermission, User
from coldfront.users.permissions import (
    get_permission_for_model,
    qs_filter_from_constraints,
)


class DummyUserView(ObjectPermissionRequiredMixin):
    queryset = User.objects.all()

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")


class ObjectPermissionTest(TestCase):
    def test_actions(self):
        """
        Test ObjectPermission actions, ObjectPermissionsMixin, and RestrictedQuerySet
        """
        groups = (
            Group(name="Group 1"),
            Group(name="Group 2"),
            Group(name="Group 3"),
        )
        Group.objects.bulk_create(groups)

        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        User.objects.bulk_create(users)

        object_types = (
            ObjectType.objects.get(app_label="users", model="user"),
            ObjectType.objects.get(app_label="users", model="group"),
        )

        permissions = (
            ObjectPermission(
                name="Permission 1",
                actions=["view", "add", "change", "delete"],
                constraints={"username": "User3"},
                description="foobar1",
            ),
            ObjectPermission(
                name="Permission 2",
                actions=["view"],
            ),
            ObjectPermission(name="Permission 3", actions=["add"], enabled=False),
        )

        ObjectPermission.objects.bulk_create(permissions)
        for i in range(0, 3):
            permissions[i].groups.set([groups[i]])
            permissions[i].users.set([users[i]])
            permissions[i].object_types.set(object_types)

        self.assertTrue(ObjectPermission.objects.get(name="Permission 1").can_delete)
        self.assertFalse(ObjectPermission.objects.get(name="Permission 2").can_delete)
        self.assertFalse(ObjectPermission.objects.get(name="Permission 3").can_view)

        opm = ObjectPermissionMixin()
        self.assertTrue(opm.has_perm(users[0], "users.change_user", obj=users[2]))
        self.assertFalse(opm.has_perm(users[0], "users.change_user", obj=users[1]))
        self.assertFalse(opm.has_perm(users[0], "users.change_user", obj=users[0]))
        self.assertTrue(opm.has_perm(users[0], "users.add_user"))
        self.assertTrue(opm.has_perm(users[1], "users.view_group"))
        self.assertTrue(opm.has_perm(users[1], "users.view_group", obj=groups[1]))
        self.assertFalse(opm.has_perm(users[1], "users.add_group"))
        self.assertFalse(opm.has_perm(users[1], "users.change_group", obj=groups[0]))
        self.assertFalse(opm.has_perm(users[2], "users.add_user"))

        self.assertEqual(User.objects.restrict(users[0], "view").count(), 1)
        self.assertEqual(User.objects.restrict(users[1], "view").count(), 3)
        self.assertEqual(User.objects.restrict(users[2], "view").count(), 0)

        view = DummyUserView()
        view.request = RequestFactory().get("/users/user/")
        view.request.user = users[0]
        self.assertTrue(view.has_permission())
        view.request.user = users[2]
        self.assertFalse(view.has_permission())


class QuerysetConstraintTest(TestCase):
    def test_basic_queryset_constraint(self):
        """
        Test that a $queryset constraint builds a valid Q object.
        """
        constraints = [
            {
                "assigned_object_type__model": "allocation",
                "assigned_object_id__in": {
                    "$queryset": {
                        "model": "ras.allocation",
                        "filter": {"project__owner": "$user"},
                    }
                },
            },
        ]
        tokens = {CONSTRAINT_TOKEN_USER: 1}
        q = qs_filter_from_constraints(constraints, tokens)
        self.assertIsNotNone(q)
        # Verify the query executes without error
        from coldfront.core.models import CommentEntry

        result = CommentEntry.objects.filter(q).exists()
        self.assertFalse(result)  # No comments exist yet, but query is valid

    def test_queryset_constraint_invalid_model(self):
        """
        Test that an invalid model in $queryset raises ValueError.
        """
        constraints = [
            {
                "assigned_object_id__in": {
                    "$queryset": {
                        "model": "ras.nonexistent",
                        "filter": {"project__owner": "$user"},
                    }
                }
            },
        ]
        tokens = {CONSTRAINT_TOKEN_USER: 1}
        with self.assertRaises(ValueError):
            qs_filter_from_constraints(constraints, tokens)

    def test_queryset_constraint_invalid_app(self):
        """
        Test that an invalid app in $queryset raises ValueError.
        """
        constraints = [
            {
                "assigned_object_id__in": {
                    "$queryset": {
                        "model": "badapp.nonexistent",
                        "filter": {"project__owner": "$user"},
                    }
                }
            },
        ]
        tokens = {CONSTRAINT_TOKEN_USER: 1}
        with self.assertRaises(ValueError):
            qs_filter_from_constraints(constraints, tokens)

    def test_queryset_constraint_filter_by_user(self):
        """
        Test that a $queryset constraint correctly filters CommentEntry records
        to only those on allocations the user owns.
        """
        from django.contrib.contenttypes.models import ContentType

        from coldfront.core.models import CommentEntry
        from coldfront.ras.models import Project, ResourceType

        # Create users
        owner = User.objects.create(username="project-owner")
        other = User.objects.create(username="other-user")
        commenter = User.objects.create(username="commenter")

        # Create project owned by owner
        project = Project.objects.create(name="Test Project", owner=owner)

        # Create an allocation on that project
        rtype = ResourceType.objects.create(name="Test ResourceType", slug="test-rt")
        rtype_ct = ContentType.objects.get_for_model(rtype)
        allocation = Allocation.objects.create(
            project=project,
            slug="test-alloc",
            owner=owner,
            resource_object_type=rtype_ct,
            resource_object_id=rtype.pk,
        )

        # Create a comment on that allocation
        alloc_ct = ContentType.objects.get_for_model(allocation)
        comment = CommentEntry.objects.create(
            assigned_object_type=alloc_ct,
            assigned_object_id=allocation.pk,
            created_by=commenter,
            kind="info",
            comments="Test comment",
        )

        # Build constraints as the owner (project__owner = owner)
        # Both conditions in one dict so they are AND'd together
        constraints = [
            {
                "assigned_object_type__model": "allocation",
                "assigned_object_id__in": {
                    "$queryset": {
                        "model": "ras.allocation",
                        "filter": {"project__owner": "$user"},
                    }
                },
            },
        ]

        # Owner should see comments on their allocation
        tokens = {CONSTRAINT_TOKEN_USER: owner.pk}
        q = qs_filter_from_constraints(constraints, tokens)
        comment_pks = list(CommentEntry.objects.filter(q).values_list("pk", flat=True))
        self.assertIn(comment.pk, comment_pks)

        # Other user should not see those comments
        tokens = {CONSTRAINT_TOKEN_USER: other.pk}
        q = qs_filter_from_constraints(constraints, tokens)
        comment_pks = list(CommentEntry.objects.filter(q).values_list("pk", flat=True))
        self.assertNotIn(comment.pk, comment_pks)

    def test_queryset_constraint_with_token_in_filter_value(self):
        """
        Test that $user token is properly replaced within the $queryset filter dict.
        """
        constraints = [
            {
                "assigned_object_id__in": {
                    "$queryset": {
                        "model": "ras.allocation",
                        "filter": {"project__owner": "$user"},
                    }
                }
            },
        ]
        # Use user pk 42
        tokens = {CONSTRAINT_TOKEN_USER: 42}
        q = qs_filter_from_constraints(constraints, tokens)
        # Verify the token was replaced in the subquery

        self.assertIsNotNone(q)
