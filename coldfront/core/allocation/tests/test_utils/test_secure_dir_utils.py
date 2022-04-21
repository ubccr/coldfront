import os

from django.core.management import call_command

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.core.allocation.models import AllocationAttributeType, \
    Allocation, AllocationStatusChoice, AllocationAttribute, \
    AllocationUserStatusChoice
from coldfront.core.allocation.utils import create_secure_dir
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
        call_command('create_directory_defaults')
        create_secure_dir(self.project1, self.subdirectory_name)

    def test_allocation_objects_created(self):
        """Testing that allocation objects are created"""
        scratch2_pl1_directory = Resource.objects.get(
            name='Scratch2 PL1 Directory')
        groups_pl1_directory = Resource.objects.get(
            name='Groups PL1 Directory')

        groups_pl1_path = \
            groups_pl1_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')
        scratch2_pl1_path = \
            scratch2_pl1_directory.resourceattribute_set.get(
                resource_attribute_type__name='path')

        groups_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=groups_pl1_directory)

        scratch2_allocation = Allocation.objects.filter(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources=scratch2_pl1_directory)

        self.assertTrue(groups_allocation.exists())
        self.assertTrue(scratch2_allocation.exists())

        groups_allocation = groups_allocation.first()
        scratch2_allocation = scratch2_allocation.first()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Directory Access')
        groups_pl1_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=groups_allocation,
            value=os.path.join(groups_pl1_path.value,
                               self.subdirectory_name))

        scratch2_pl1_subdirectory = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=scratch2_allocation,
            value=os.path.join(scratch2_pl1_path.value,
                               self.subdirectory_name))

        self.assertTrue(groups_pl1_subdirectory.exists())
        self.assertTrue(scratch2_pl1_subdirectory.exists())

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
