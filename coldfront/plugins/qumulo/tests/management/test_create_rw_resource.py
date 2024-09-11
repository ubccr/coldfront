from django.test import TestCase

# jprew - TODO - change this command name
from coldfront.plugins.qumulo.management.commands.add_qumulo_resource import Command
from coldfront.core.resource.models import Resource, ResourceType


class CreateResource(TestCase):
    def setUp(self):
        self.storage_obj = ResourceType.objects.get_or_create(name="Storage")
        self.acl_resource_type, self.created = ResourceType.objects.get_or_create(
            name="ACL"
        )

    def test_creates_rw_resource(self):
        cmd = Command()
        cmd.handle()

        # Check if the rw Resource was created with correct attributes
        rw_resource = Resource.objects.get(name="rw")
        self.assertEqual(rw_resource.description, "RW ACL")
        self.assertEqual(rw_resource.resource_type.name, "ACL")
        self.assertTrue(rw_resource.is_available)
        self.assertFalse(rw_resource.is_public)
        self.assertTrue(rw_resource.is_allocatable)
        self.assertFalse(rw_resource.requires_payment)

        # Check if the ro Resource was created with correct attributes
        ro_resource = Resource.objects.get(name="rw")
        self.assertEqual(ro_resource.description, "RW ACL")
        self.assertEqual(ro_resource.resource_type.name, "ACL")
        self.assertTrue(ro_resource.is_available)
        self.assertFalse(ro_resource.is_public)
        self.assertTrue(ro_resource.is_allocatable)
        self.assertFalse(ro_resource.requires_payment)
