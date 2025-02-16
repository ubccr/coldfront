from coldfront.core.test_helpers.factories import UserFactory
from coldfront.core.user.models import UserProfile, ApproverProfile
from coldfront.core.school.models import School
from django.test import TestCase
from django.contrib.auth.models import Permission

class TestUserProfile(TestCase):
    class Data:
        """Collection of test data, separated for readability"""

        def __init__(self):
            self.user = UserFactory(username='approver_user')
            self.non_approver_user = UserFactory(username='regular_user')

            self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user)
            self.non_approver_profile, _ = UserProfile.objects.get_or_create(user=self.non_approver_user)

            self.permission = Permission.objects.get(codename="can_review_allocation_requests")
            self.user.user_permissions.add(self.permission)

            self.school1 = School.objects.create(description="Tandon School of Engineering")
            self.school2 = School.objects.create(description="NYU IT")
            self.school3 = School.objects.create(description="Arts & Science")

            self.initial_fields = {
                'user': self.user,
                'is_pi': False,
                'id': self.user.id
            }
            
            self.unsaved_object = UserProfile(**self.initial_fields)
    
    def setUp(self):
        self.data = self.Data()

    def test_fields_generic(self):
        """Test that UserProfile fields are correctly saved and retrieved."""
        profile_obj = self.data.unsaved_object
        profile_obj.save()

        # Ensure only one UserProfile exists for this user
        self.assertEqual(1, UserProfile.objects.filter(user=self.data.user).count())

        retrieved_profile = UserProfile.objects.get(pk=profile_obj.pk)

        for item in self.data.initial_fields.items():
            (field, initial_value) = item
            with self.subTest(item=item):
                saved_value = getattr(retrieved_profile, field)
                self.assertEqual(initial_value, saved_value)
        self.assertEqual(profile_obj, retrieved_profile)

    def test_user_on_delete(self):
        """Test that deleting a User also deletes the related UserProfile (CASCADE)."""
        profile_obj = self.data.unsaved_object
        profile_obj.save()

        # Ensure only the specific user's UserProfile is considered
        self.assertEqual(1, UserProfile.objects.filter(user=self.data.user).count())

        profile_obj.user.delete()

        # expecting CASCADE
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(pk=profile_obj.pk)

        # Only this user's UserProfile should be deleted
        self.assertEqual(0, UserProfile.objects.filter(user=self.data.user).count())

    def test_is_approver(self):
        """Test if a user is correctly identified as an approver."""
        self.assertTrue(self.data.user_profile.is_approver())
        self.assertFalse(self.data.non_approver_profile.is_approver())

    def test_approver_profile_creation(self):
        """Test that ApproverProfile is created automatically when an approver sets schools."""
        self.assertFalse(ApproverProfile.objects.filter(user_profile=self.data.user_profile).exists())

        # Assign schools to the approver
        self.data.user_profile.schools = ["Tandon School of Engineering", "NYU IT"]

        # Ensure ApproverProfile is created
        self.assertTrue(ApproverProfile.objects.filter(user_profile=self.data.user_profile).exists())

        # Convert both lists to sets to ignore order
        expected_schools = {"Tandon School of Engineering", "NYU IT"}
        actual_schools = set(self.data.user_profile.schools)

        self.assertEqual(expected_schools, actual_schools)

    def test_non_approver_cannot_set_schools(self):
        """Test that a non-approver cannot set schools and raises ValueError."""
        with self.assertRaises(ValueError):
            self.data.non_approver_profile.schools = ["Tandon School of Engineering"]

    def test_schools_property_getter(self):
        """Test getting the list of schools for an approver (order-independent)."""
        approver_profile = ApproverProfile.objects.create(user_profile=self.data.user_profile)
        approver_profile.schools.set([self.data.school1, self.data.school2])

        # Convert both lists to sets to ignore order
        expected_schools = {"Tandon School of Engineering", "NYU IT"}
        actual_schools = set(self.data.user_profile.schools)

        self.assertEqual(expected_schools, actual_schools)

    def test_schools_property_setter(self):
        """Test setting schools through the schools property."""
        self.data.user_profile.schools = ["Arts & Science"]
        approver_profile = ApproverProfile.objects.get(user_profile=self.data.user_profile)

        self.assertEqual(list(approver_profile.schools.values_list('description', flat=True)),
                         ["Arts & Science"])
