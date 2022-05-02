import os

from django.core.management import call_command

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.core.allocation.models import AllocationAttributeType, \
    Allocation, AllocationStatusChoice, AllocationAttribute, \
    AllocationUserStatusChoice, SecureDirAddUserRequest, \
    SecureDirAddUserRequestStatusChoice, SecureDirRemoveUserRequest, \
    SecureDirRemoveUserRequestStatusChoice
from coldfront.core.allocation.utils import create_secure_dir, \
    get_secure_dir_manage_user_request_objects
from coldfront.core.project.models import ProjectUser, ProjectUserRoleChoice, \
    ProjectUserStatusChoice
from coldfront.core.resource.models import Resource


class TestCreateSecureDir(TestAllocationBase):
    """A class for testing create_secure_dir."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        pi = ProjectUser.objects.get(project=self.project1,
                                     user=self.pi,
                                     status=ProjectUserStatusChoice.objects.get(
                                         name='Active'))
        pi.role = ProjectUserRoleChoice.objects.get(name='Principal '
                                                         'Investigator')
        pi.save()

        self.subdirectory_name = 'test_dir'
        call_command('add_directory_defaults')
        create_secure_dir(self.project1, self.subdirectory_name)

    def test_allocation_objects_created(self):
        """Testing that allocation objects are created"""
        scratch2_p2p3_directory = Resource.objects.get(
            name='Scratch2 P2/P3 Directory')
        groups_p2p3_directory = Resource.objects.get(
            name='Groups P2/P3 Directory')

        groups_p2p3_path = \
            groups_p2p3_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')
        scratch2_p2p3_path = \
            scratch2_p2p3_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')

        groups_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=groups_p2p3_directory)

        scratch2_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=scratch2_p2p3_directory)

        self.assertTrue(groups_allocation.exists())
        self.assertTrue(scratch2_allocation.exists())

        groups_allocation = groups_allocation.first()
        scratch2_allocation = scratch2_allocation.first()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Directory Access')
        groups_p2p3_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=groups_allocation,
            value=os.path.join(groups_p2p3_path.value,
                               self.subdirectory_name))

        scratch2_p2p3_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=scratch2_allocation,
            value=os.path.join(scratch2_p2p3_path.value,
                               self.subdirectory_name))

        self.assertTrue(groups_p2p3_subdirectory.exists())
        self.assertTrue(scratch2_p2p3_subdirectory.exists())

        # Test that AllocationUsers are created for PIs
        self.assertEqual(groups_allocation.allocationuser_set.count(), 1)
        self.assertEqual(scratch2_allocation.allocationuser_set.count(), 1)

        active_status = AllocationUserStatusChoice.objects.get(name='Active')
        pi_groups_alloc_user = \
            groups_allocation.allocationuser_set.filter(
                user=self.pi,
                status=active_status)
        self.assertTrue(pi_groups_alloc_user.exists())

        pi_scratch2_alloc_user = \
            scratch2_allocation.allocationuser_set.filter(
                user=self.pi,
                status=active_status)
        self.assertTrue(pi_scratch2_alloc_user.exists())


class TestGetSecureDirManageUserRequestObjects(TestAllocationBase):
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
