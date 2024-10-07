from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import Group, Permission
from coldfront.core.group.management.commands.create_default_user_groups import (
    DEFAULT_RIS_USERSUPPORT_GROUP_PERMISSIONS,
)


class CreateDefaultUserGroupsTest(TestCase):
    """
    Test the create_default_user_groups management command
    """

    # POSITIVE TESTS
    # Test that the command creates the RIS-UserSupport group
    def test_ris_usersupport_group_created(self):
        call_command("create_default_user_groups")
        group = Group.objects.filter(name="RIS-UserSupport").first()
        self.assertIsNotNone(group)

    # Test that the RIS-UserSupport group has all the permissions in the DEFAULT_RIS_USERSUPPORT_GROUP_PERMISSIONS list
    def test_ris_usersupport_group_expected_permissions(self):
        call_command("create_default_user_groups")
        group = Group.objects.filter(name="RIS-UserSupport").first()
        group_permissions = group.permissions.all()
        expected_permissions = Permission.objects.filter(
            id__in=[
                permission["id"]
                for permission in DEFAULT_RIS_USERSUPPORT_GROUP_PERMISSIONS
            ]
        ).all()
        self.assertEqual(
            set(group_permissions),
            set(expected_permissions),
        )

    # NEGATIVE TESTS
    # Test that the RIS-UserSupport group DOES NOT have all permissions in the auth_permission table
    def test_ris_usersupport_group_all_permissions(self):
        call_command("create_default_user_groups")
        group = Group.objects.filter(name="RIS-UserSupport").first()
        group_permissions = group.permissions.all()
        all_permissions = Permission.objects.all()
        self.assertNotEqual(
            set(group_permissions),
            set(all_permissions),
        )

    # Test that the RIS-BadTestGroup group was not created
    def test_ris_badtestgroup_group_created(self):
        call_command("create_default_user_groups")
        group = Group.objects.filter(name="RIS-BadTestGroup").first()
        self.assertIsNone(group)
