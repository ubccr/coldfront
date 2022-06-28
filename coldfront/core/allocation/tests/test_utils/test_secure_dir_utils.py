import os

from django.contrib.auth.models import User
from django.core.management import call_command

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.core.allocation.models import AllocationAttributeType, \
    Allocation, AllocationStatusChoice, AllocationAttribute, \
    AllocationUserStatusChoice, SecureDirAddUserRequest, \
    SecureDirAddUserRequestStatusChoice, SecureDirRemoveUserRequest, \
    SecureDirRemoveUserRequestStatusChoice
from coldfront.core.allocation.utils_.secure_dir_utils import \
    create_secure_dirs, get_secure_dir_manage_user_request_objects
from coldfront.core.project.models import ProjectUser, ProjectUserRoleChoice, \
    ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import TestBase


class TestCreateSecureDir(TestBase):
    """A class for testing create_secure_dirs."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        self.project1 = self.create_active_project_with_pi('project1', self.pi)

        self.subdirectory_name = 'test_dir'
        call_command('add_directory_defaults')
        create_secure_dirs(self.project1, self.subdirectory_name, 'groups')
        create_secure_dirs(self.project1, self.subdirectory_name, 'scratch')

    def test_allocation_objects_created(self):
        """Testing that allocation objects are created"""
        scratch_p2p3_directory = Resource.objects.get(
            name='Scratch P2/P3 Directory')
        groups_p2p3_directory = Resource.objects.get(
            name='Groups P2/P3 Directory')

        groups_p2p3_path = \
            groups_p2p3_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')
        scratch_p2p3_path = \
            scratch_p2p3_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')

        groups_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=groups_p2p3_directory)

        scratch_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=scratch_p2p3_directory)

        self.assertTrue(groups_allocation.exists())
        self.assertTrue(scratch_allocation.exists())

        groups_allocation = groups_allocation.first()
        scratch_allocation = scratch_allocation.first()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Directory Access')
        groups_p2p3_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=groups_allocation,
            value=os.path.join(groups_p2p3_path.value,
                               self.subdirectory_name))

        scratch_p2p3_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=scratch_allocation,
            value=os.path.join(scratch_p2p3_path.value,
                               self.subdirectory_name))

        self.assertTrue(groups_p2p3_subdirectory.exists())
        self.assertTrue(scratch_p2p3_subdirectory.exists())


class TestGetSecureDirManageUserRequestObjects(TestBase):
    """A class for testing get_secure_dir_manage_user_request_objects."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        call_command('add_directory_defaults')

    def test_action_add(self):
        """Testing that the correct fields are set when action=add"""
        class DummyObject:
            pass

        dummy_object = DummyObject()

        get_secure_dir_manage_user_request_objects(dummy_object, 'add')

        self.assertEqual(dummy_object.action, 'add')
        self.assertEqual(dummy_object.add_bool, True)
        self.assertEqual(dummy_object.request_obj, SecureDirAddUserRequest)
        self.assertEqual(dummy_object.request_status_obj,
                         SecureDirAddUserRequestStatusChoice)
        self.assertEqual(dummy_object.language_dict['preposition'], 'to')
        self.assertEqual(dummy_object.language_dict['noun'], 'addition')
        self.assertEqual(dummy_object.language_dict['verb'], 'add')

    def test_action_remove(self):
        """Testing that the correct fields are set when action=add"""
        class DummyObject:
            pass

        dummy_object = DummyObject()

        get_secure_dir_manage_user_request_objects(dummy_object, 'remove')

        self.assertEqual(dummy_object.action, 'remove')
        self.assertEqual(dummy_object.add_bool, False)
        self.assertEqual(dummy_object.request_obj, SecureDirRemoveUserRequest)
        self.assertEqual(dummy_object.request_status_obj,
                         SecureDirRemoveUserRequestStatusChoice)
        self.assertEqual(dummy_object.language_dict['preposition'], 'from')
        self.assertEqual(dummy_object.language_dict['noun'], 'removal')
        self.assertEqual(dummy_object.language_dict['verb'], 'remove')
