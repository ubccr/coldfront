from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.tests.test_billing_base import TestBillingBase
from coldfront.core.billing.utils import ProjectBillingActivityManager
from coldfront.core.billing.utils import ProjectUserBillingActivityManager
from coldfront.core.billing.utils import UserBillingActivityManager
from coldfront.core.billing.utils.queries import get_or_create_billing_activity_from_full_id
from coldfront.core.user.models import UserProfile


class TestBillingActivityManagerBase(TestBillingBase):
    """A base class for testing billing activity manager utility
    classes."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.billing_id_1 = '123456-789'
        self.billing_activity_1 = get_or_create_billing_activity_from_full_id(
            self.billing_id_1)
        self.billing_id_2 = '987654-321'
        self.billing_activity_2 = get_or_create_billing_activity_from_full_id(
            self.billing_id_2)


class TestProjectBillingActivityManager(TestBillingActivityManagerBase):
    """A class for testing the ProjectBillingActivityManager utility
    class."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self.manager = ProjectBillingActivityManager(self.project)

    def test_get_invalid_allocation_attribute_value(self):
        """Test that the getter raises an exception when the given
        Project's AllocationAttribute contains a value that does not
        correspond to a BillingActivity."""
        allocation_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'value': 'invalid',
        }
        allocation_attribute = AllocationAttribute.objects.create(
            **allocation_attribute_kwargs)
        with self.assertRaises(ValueError) as cm:
            _ = self.manager.billing_activity
        self.assertIn('invalid literal', str(cm.exception))

        allocation_attribute.value = str(
            self.billing_activity_1.pk + self.billing_activity_2.pk + 1)
        allocation_attribute.save()

        with self.assertRaises(BillingActivity.DoesNotExist) as cm:
            _ = self.manager.billing_activity
        self.assertIn('does not exist', str(cm.exception))

    def test_get_nonexistent_allocation_attribute(self):
        """Test that the getter returns None when the given Project does
        not have an associated AllocationAttribute for storing a
        BillingActivity, but returns the contained BillingActivity once
        it has been created."""
        allocation_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
        }
        self.assertFalse(
            AllocationAttribute.objects.filter(**allocation_attribute_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        allocation_attribute_kwargs['value'] = str(self.billing_activity_1.pk)
        AllocationAttribute.objects.create(**allocation_attribute_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

    def test_get_refreshes_value(self):
        """Test that the getter returns the most up-to-date
        BillingActivity stored in the AllocationAttribute, accounting
        for changes from elsewhere."""
        allocation_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'value': str(self.billing_activity_1.pk),
        }
        allocation_attribute = AllocationAttribute.objects.create(
            **allocation_attribute_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

        allocation_attribute.value = str(self.billing_activity_2.pk)
        allocation_attribute.save()
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_2)

        allocation_attribute.delete()
        self.assertIsNone(self.manager.billing_activity)

    def test_set_creates_allocation_attribute_if_nonexistent(self):
        """Test that the setter creates an associated
        AllocationAttribute for the Project if one does not already
        exist."""
        allocation_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
        }
        self.assertFalse(
            AllocationAttribute.objects.filter(**allocation_attribute_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_1

        allocation_attribute_kwargs['value'] = str(self.billing_activity_1.pk)
        try:
            allocation_attribute = AllocationAttribute.objects.get(
                **allocation_attribute_kwargs)
        except AllocationAttribute.DoesNotExist:
            self.fail('An AllocationAttribute should have been created.')
        old_attribute_pk = allocation_attribute.pk

        allocation_attribute.delete()
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_2
        allocation_attribute_kwargs.pop('value')
        try:
            allocation_attribute = AllocationAttribute.objects.get(
                **allocation_attribute_kwargs)
        except AllocationAttribute.DoesNotExist:
            self.fail('An AllocationAttribute should have been created.')
        new_attribute_pk = allocation_attribute.pk

        self.assertGreater(new_attribute_pk, old_attribute_pk)

    def test_set_updates_allocation_attribute_if_existent(self):
        """Test that the setter updates an associated
        AllocationAttribute for the Project if one already exists."""
        allocation_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
        }

        self.manager.billing_activity = self.billing_activity_1
        allocation_attribute = AllocationAttribute.objects.get(
            **allocation_attribute_kwargs)
        self.assertEqual(
            allocation_attribute.value, str(self.billing_activity_1.pk))

        self.manager.billing_activity = self.billing_activity_2
        allocation_attribute.refresh_from_db()
        self.assertEqual(
            allocation_attribute.value, str(self.billing_activity_2.pk))


class TestProjectUserBillingActivityManager(TestBillingActivityManagerBase):
    """A class for testing the ProjectUserBillingActivityManager utility
    class."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.allocation_user = AllocationUser.objects.get(
            allocation=self.allocation, user=self.user)
        self.allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self.manager = ProjectUserBillingActivityManager(self.project_user)

    def test_get_invalid_allocation_user_attribute_value(self):
        """Test that the getter raises an exception when the given
        ProjectUser's AllocationUserAttribute contains a value that does
        not correspond to a BillingActivity."""
        allocation_user_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'allocation_user': self.allocation_user,
            'value': 'invalid',
        }
        allocation_user_attribute = AllocationUserAttribute.objects.create(
            **allocation_user_attribute_kwargs)
        with self.assertRaises(ValueError) as cm:
            _ = self.manager.billing_activity
        self.assertIn('invalid literal', str(cm.exception))

        allocation_user_attribute.value = str(
            self.billing_activity_1.pk + self.billing_activity_2.pk + 1)
        allocation_user_attribute.save()

        with self.assertRaises(BillingActivity.DoesNotExist) as cm:
            _ = self.manager.billing_activity
        self.assertIn('does not exist', str(cm.exception))

    def test_get_nonexistent_allocation_user_attribute(self):
        """Test that the getter returns None when the given ProjectUser
        does not have an associated AllocationUserAttribute for storing
        a BillingActivity, but returns the contained BillingActivity
        once it has been created."""
        allocation_user_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'allocation_user': self.allocation_user,
        }
        self.assertFalse(
            AllocationUserAttribute.objects.filter(
                **allocation_user_attribute_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        allocation_user_attribute_kwargs['value'] = str(
            self.billing_activity_1.pk)
        AllocationUserAttribute.objects.create(
            **allocation_user_attribute_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

    def test_get_refreshes_value(self):
        """Test that the getter returns the most up-to-date
        BillingActivity stored in the AllocationUserAttribute,
        accounting for changes from elsewhere."""
        allocation_user_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'allocation_user': self.allocation_user,
            'value': str(self.billing_activity_1.pk),
        }
        allocation_user_attribute = AllocationUserAttribute.objects.create(
            **allocation_user_attribute_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

        allocation_user_attribute.value = str(self.billing_activity_2.pk)
        allocation_user_attribute.save()
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_2)

        allocation_user_attribute.delete()
        self.assertIsNone(self.manager.billing_activity)

    def test_set_creates_allocation_user_attribute_if_nonexistent(self):
        """Test that the setter creates an associated
        AllocationUserAttribute for the ProjectUser if one does not
        already exist."""
        allocation_user_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'allocation_user': self.allocation_user,
        }
        self.assertFalse(
            AllocationUserAttribute.objects.filter(
                **allocation_user_attribute_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_1

        allocation_user_attribute_kwargs['value'] = str(
            self.billing_activity_1.pk)
        try:
            allocation_user_attribute = AllocationUserAttribute.objects.get(
                **allocation_user_attribute_kwargs)
        except AllocationUserAttribute.DoesNotExist:
            self.fail('An AllocationUserAttribute should have been created.')
        old_attribute_pk = allocation_user_attribute.pk

        allocation_user_attribute.delete()
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_2
        allocation_user_attribute_kwargs.pop('value')
        try:
            allocation_user_attribute = AllocationUserAttribute.objects.get(
                **allocation_user_attribute_kwargs)
        except AllocationUserAttribute.DoesNotExist:
            self.fail('An AllocationUserAttribute should have been created.')
        new_attribute_pk = allocation_user_attribute.pk

        self.assertGreater(new_attribute_pk, old_attribute_pk)

    def test_set_updates_allocation_user_attribute_if_existent(self):
        """Test that the setter updates an associated
        AllocationUserAttribute for the ProjectUser if one already
        exists."""
        allocation_user_attribute_kwargs = {
            'allocation_attribute_type': self.allocation_attribute_type,
            'allocation': self.allocation,
            'allocation_user': self.allocation_user,
        }
        self.manager.billing_activity = self.billing_activity_1
        allocation_user_attribute = AllocationUserAttribute.objects.get(
            **allocation_user_attribute_kwargs)
        self.assertEqual(
            allocation_user_attribute.value, str(self.billing_activity_1.pk))

        self.manager.billing_activity = self.billing_activity_2
        allocation_user_attribute.refresh_from_db()
        self.assertEqual(
            allocation_user_attribute.value, str(self.billing_activity_2.pk))


class TestUserBillingActivityManager(TestBillingActivityManagerBase):
    """A class for testing the UserBillingActivityManager utility
    class."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.user.userprofile.delete()
        self.manager = UserBillingActivityManager(self.user)

    def test_get_nonexistent_user_profile(self):
        """Test that the getter returns None when the given User does
        not have an associated UserProfile for storing a
        BillingActivity, but returns the contained BillingActivity once
        it has been created."""
        user_profile_kwargs = {
            'user': self.user,
        }
        self.assertFalse(UserProfile.objects.filter(**user_profile_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        user_profile_kwargs['billing_activity'] = self.billing_activity_1
        UserProfile.objects.create(**user_profile_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

    def test_get_refreshes_value(self):
        """Test that the getter returns the most up-to-date
        BillingActivity stored in the UserProfile, accounting for
        changes from elsewhere."""
        user_profile_kwargs = {
            'user': self.user,
            'billing_activity': self.billing_activity_1,
        }
        user_profile = UserProfile.objects.create(**user_profile_kwargs)
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_1)

        user_profile.billing_activity = self.billing_activity_2
        user_profile.save()
        self.assertEqual(
            self.manager.billing_activity, self.billing_activity_2)

        user_profile.delete()
        self.assertIsNone(self.manager.billing_activity)

    def test_set_creates_user_profile_if_nonexistent(self):
        """Test that the setter creates an associated UserProfile for
        the User if one does not already exist."""
        user_profile_kwargs = {
            'user': self.user,
        }
        self.assertFalse(UserProfile.objects.filter(**user_profile_kwargs))
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_1

        user_profile_kwargs['billing_activity'] = self.billing_activity_1
        try:
            user_profile = UserProfile.objects.get(**user_profile_kwargs)
        except UserProfile.DoesNotExist:
            self.fail('A UserProfile should have been created.')
        old_profile_pk = user_profile.pk

        user_profile.delete()
        self.assertIsNone(self.manager.billing_activity)

        self.manager.billing_activity = self.billing_activity_2
        user_profile_kwargs.pop('billing_activity')
        try:
            user_profile = UserProfile.objects.get(**user_profile_kwargs)
        except UserProfile.DoesNotExist:
            self.fail('A UserProfile should have been created.')
        new_profile_pk = user_profile.pk

        self.assertGreater(new_profile_pk, old_profile_pk)

    def test_set_updates_user_profile_if_existent(self):
        """Test that the setter updates an associated UserProfile for
        the User if one already exists."""
        user_profile_kwargs = {
            'user': self.user,
        }

        self.manager.billing_activity = self.billing_activity_1
        user_profile = UserProfile.objects.get(**user_profile_kwargs)
        self.assertEqual(
            user_profile.billing_activity, self.billing_activity_1)

        self.manager.billing_activity = self.billing_activity_2
        user_profile.refresh_from_db()
        self.assertEqual(
            user_profile.billing_activity, self.billing_activity_2)
