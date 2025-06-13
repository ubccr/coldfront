import json
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from coldfront.core.user.models import UserProfile, ApproverProfile
from coldfront.core.school.models import School
from coldfront.core.user.management.commands.load_approver_schools import (
    load_approver_schools,
)


class LoadApproverSchoolsTest(TestCase):
    """Tests for load_approver_schools function."""

    def setUp(self):
        """Set up test users, schools, and permissions."""
        # Create users
        self.approver1 = User.objects.create(username="approver1", is_staff=False)
        self.approver2 = User.objects.create(username="approver2", is_staff=False)
        self.non_existent_user = "nonuser"  # This user does not exist

        # Get UserProfiles
        self.approver1_profile = UserProfile.objects.get(user=self.approver1)
        self.approver2_profile = UserProfile.objects.get(user=self.approver2)

        # Create Schools
        self.school1 = School.objects.create(description="Tandon School of Engineering")
        self.school2 = School.objects.create(description="NYU IT")

        # Create permission
        self.review_permission = Permission.objects.get(
            codename="can_review_allocation_requests"
        )

        # Sample JSON Data
        self.json_data = {
            "approver1": ["Tandon School of Engineering", "NYU IT"],
            "approver2": ["NYU IT"],
            "nonuser": ["NYU IT"],  # This user does not exist
        }

    def test_users_are_assigned_as_staff(self):
        """Test that users are correctly marked as staff after function execution."""
        load_approver_schools(self.json_data)

        self.approver1.refresh_from_db()
        self.approver2.refresh_from_db()

        self.assertTrue(self.approver1.is_staff)
        self.assertTrue(self.approver2.is_staff)

    def test_users_are_granted_approver_permission(self):
        """Test that users receive the 'can_review_allocation_requests' permission."""
        load_approver_schools(self.json_data)

        self.assertTrue(
            self.approver1.has_perm("allocation.can_review_allocation_requests")
        )
        self.assertTrue(
            self.approver2.has_perm("allocation.can_review_allocation_requests")
        )

    def test_approver_profiles_are_created(self):
        """Test that an ApproverProfile is created for approvers."""
        load_approver_schools(self.json_data)

        self.assertTrue(
            ApproverProfile.objects.filter(user_profile=self.approver1_profile).exists()
        )
        self.assertTrue(
            ApproverProfile.objects.filter(user_profile=self.approver2_profile).exists()
        )

    def test_schools_are_assigned_correctly(self):
        """Test that users are assigned the correct schools in their ApproverProfile."""
        load_approver_schools(self.json_data)

        approver1_profile = ApproverProfile.objects.get(
            user_profile=self.approver1_profile
        )
        approver2_profile = ApproverProfile.objects.get(
            user_profile=self.approver2_profile
        )

        self.assertEqual(
            set(approver1_profile.schools.values_list("description", flat=True)),
            {"Tandon School of Engineering", "NYU IT"},
        )
        self.assertEqual(
            set(approver2_profile.schools.values_list("description", flat=True)),
            {"NYU IT"},
        )

    def test_nonexistent_user_is_skipped(self):
        """Test that non-existent users are skipped without error."""
        load_approver_schools(self.json_data)

        # Ensure no UserProfile or ApproverProfile is created for the non-existent user
        self.assertFalse(UserProfile.objects.filter(user__username="jdoe").exists())
        self.assertFalse(
            ApproverProfile.objects.filter(user_profile__user__username="jdoe").exists()
        )

    def test_function_does_not_duplicate_existing_profiles(self):
        """Test that the function does not create duplicate ApproverProfiles when run multiple times."""
        load_approver_schools(self.json_data)  # First execution
        load_approver_schools(self.json_data)  # Second execution

        # Ensure only one ApproverProfile per user
        self.assertEqual(
            ApproverProfile.objects.filter(user_profile=self.approver1_profile).count(),
            1,
        )
        self.assertEqual(
            ApproverProfile.objects.filter(user_profile=self.approver2_profile).count(),
            1,
        )
