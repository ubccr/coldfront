from django.test import TestCase
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings
from django.core.management import call_command
from coldfront.core.resource.management.commands.add_university_school_default_resources import (
    Command,
)
import tempfile
import json
import os
from pathlib import Path

GENERAL_RESOURCE_NAME = import_from_settings("GENERAL_RESOURCE_NAME")


class AddUniversityAndGenericResourcesTestCase(TestCase):
    def setUp(self):
        # create the two ResourceTypes this method uses
        self.cluster_rt, _ = ResourceType.objects.get_or_create(
            name="Cluster", description="Cluster servers"
        )
        self.generic_rt, _ = ResourceType.objects.get_or_create(
            name="Generic", description="Generic School"
        )

        # create the two School entries
        self.tandon, _ = School.objects.get_or_create(
            description="Tandon School of Engineering"
        )
        self.cds, _ = School.objects.get_or_create(
            description="Center for Data Science"
        )

        # instantiate your management command
        self.cmd = Command()

    def test_creates_all_5_resources_with_correct_fields(self):
        # run the method under test
        self.cmd.add_general_university_resource()

        # there should be exactly 5 Resources
        self.assertEqual(Resource.objects.count(), 1)

        # 1) University cluster
        uni = Resource.objects.get(name=GENERAL_RESOURCE_NAME)
        self.assertEqual(uni.resource_type, self.cluster_rt)
        self.assertIsNone(uni.school)
        self.assertEqual(uni.description, "University Academic Cluster")
        self.assertTrue(uni.is_available)
        self.assertTrue(uni.is_public)
        self.assertTrue(uni.is_allocatable)

    def test_add_school_resources_with_custom_path(self):
        # 1) write out a tiny JSON file
        sample = [
            {
                "resource_type": "Generic",
                "parent_resource": None,
                "name": "Test",
                "description": "Test",
                "school": "Tandon School of Engineering",
                "is_available": True,
                "is_public": False,
                "is_allocatable": True,
            },
        ]
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            json.dump(sample, f)
            f.flush()
            tmp_path = f.name

        # 2) invoke your management command with --json-file-path
        call_command(
            "add_university_school_default_resources",  # or whatever your command name is
            json_file_path=tmp_path,
        )
        # 3) 1 General University Resource + 1 School Resource created
        self.assertEqual(Resource.objects.count(), 2)
        # cleanup
        os.remove(tmp_path)

    def test_add_school_resources(self):
        test_file_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "test_school_resources.json"
        )
        # run the method under test
        call_command(
            "add_university_school_default_resources",  # or whatever your command name is
            json_file_path=test_file_path,
        )

        # there should be exactly 4 Resources
        self.assertEqual(Resource.objects.count(), 5)

        university_general = Resource.objects.get(name=GENERAL_RESOURCE_NAME)

        # 1) Tandon
        tandon = Resource.objects.get(name="Tandon")
        self.assertEqual(tandon.resource_type, self.generic_rt)
        self.assertEqual(tandon.school, self.tandon)
        self.assertEqual(tandon.parent_resource, university_general)
        self.assertEqual(tandon.description, "Tandon-wide-resources")
        self.assertTrue(tandon.is_available)
        self.assertFalse(tandon.is_public)
        self.assertTrue(tandon.is_allocatable)

        # 2) Tandon-GPU-Adv
        tga = Resource.objects.get(name="Tandon-GPU-Adv")
        self.assertEqual(tga.resource_type, self.generic_rt)
        self.assertEqual(tga.school, self.tandon)
        self.assertEqual(tga.parent_resource, university_general)
        self.assertEqual(tga.description, "Advanced GPU resource")
        self.assertTrue(tga.is_available)
        self.assertFalse(tga.is_public)
        self.assertTrue(tga.is_allocatable)

        # 3) CDS
        cds = Resource.objects.get(name="CDS")
        self.assertEqual(cds.resource_type, self.generic_rt)
        self.assertEqual(cds.school, self.cds)
        self.assertEqual(cds.parent_resource, university_general)
        self.assertEqual(cds.description, "CDS-wide-resources")
        self.assertTrue(cds.is_available)
        self.assertFalse(cds.is_public)
        self.assertTrue(cds.is_allocatable)

        # 4) CDS-GPU-Prio
        cdg = Resource.objects.get(name="CDS-GPU-Prio")
        self.assertEqual(cdg.resource_type, self.generic_rt)
        self.assertEqual(cdg.school, self.cds)
        self.assertEqual(cdg.parent_resource, university_general)
        self.assertEqual(cdg.description, "Priority GPU resource")
        self.assertTrue(cdg.is_available)
        self.assertFalse(cdg.is_public)
        self.assertTrue(cdg.is_allocatable)

    def test_idempotent(self):
        # calling it twice shouldn't create duplicates
        test_file_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "test_school_resources.json"
        )
        call_command(
            "add_university_school_default_resources",  # or whatever your command name is
            json_file_path=test_file_path,
        )
        self.assertEqual(Resource.objects.count(), 5)
