from django.test import TestCase

from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings

# adjust this import to your command’s module path:
from coldfront.core.resource.management.commands.add_resource_defaults import Command

GENERAL_RESOURCE_NAME = import_from_settings('GENERAL_RESOURCE_NAME')


class AddUniversityAndGenericResourcesTestCase(TestCase):
    def setUp(self):
        # create the two ResourceTypes this method uses
        self.cluster_rt, _ = ResourceType.objects.get_or_create(
            name='Cluster', description='Cluster servers'
        )
        self.generic_rt, _ = ResourceType.objects.get_or_create(
            name='Generic', description='Generic School'
        )

        # create the two School entries
        self.tandon, _ = School.objects.get_or_create(
            description='Tandon School of Engineering'
        )
        self.cds, _ = School.objects.get_or_create(
            description='Center for Data Science'
        )

        # instantiate your management command
        self.cmd = Command()

    def test_creates_all_5_resources_with_correct_fields(self):
        # run the method under test
        self.cmd.add_university_and_generic_resources()

        # there should be exactly 5 Resources
        self.assertEqual(Resource.objects.count(), 5)

        # 1) University cluster
        uni = Resource.objects.get(name=GENERAL_RESOURCE_NAME)
        self.assertEqual(uni.resource_type, self.cluster_rt)
        self.assertIsNone(uni.school)
        self.assertEqual(uni.description, 'University Academic Cluster')
        self.assertTrue(uni.is_available)
        self.assertTrue(uni.is_public)
        self.assertTrue(uni.is_allocatable)

        # 2) Tandon
        tandon = Resource.objects.get(name='Tandon')
        self.assertEqual(tandon.resource_type, self.generic_rt)
        self.assertEqual(tandon.school, self.tandon)
        self.assertEqual(tandon.description, 'Tandon-wide-resources')
        self.assertTrue(tandon.is_available)
        self.assertFalse(tandon.is_public)
        self.assertTrue(tandon.is_allocatable)

        # 3) Tandon-GPU-Adv
        tga = Resource.objects.get(name='Tandon-GPU-Adv')
        self.assertEqual(tga.resource_type, self.generic_rt)
        self.assertEqual(tga.school, self.tandon)
        self.assertEqual(tga.description, 'Advanced GPU resource')
        self.assertTrue(tga.is_available)
        self.assertFalse(tga.is_public)
        self.assertTrue(tga.is_allocatable)

        # 4) CDS
        cds = Resource.objects.get(name='CDS')
        self.assertEqual(cds.resource_type, self.generic_rt)
        self.assertEqual(cds.school, self.cds)
        self.assertEqual(cds.description, 'CDS-wide-resources')
        self.assertTrue(cds.is_available)
        self.assertFalse(cds.is_public)
        self.assertTrue(cds.is_allocatable)

        # 5) CDS-GPU-Prio
        cdg = Resource.objects.get(name='CDS-GPU-Prio')
        self.assertEqual(cdg.resource_type, self.generic_rt)
        self.assertEqual(cdg.school, self.cds)
        self.assertEqual(cdg.description, 'Priority GPU resource')
        self.assertTrue(cdg.is_available)
        self.assertFalse(cdg.is_public)
        self.assertTrue(cdg.is_allocatable)

    def test_idempotent(self):
        # calling it twice shouldn't create duplicates
        self.cmd.add_university_and_generic_resources()
        self.cmd.add_university_and_generic_resources()
        self.assertEqual(Resource.objects.count(), 5)
