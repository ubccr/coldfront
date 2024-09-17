from coldfront.core.resource.models import Resource, ResourceType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Adding Storage2/Qumulo resources")
        storage_resource_type = ResourceType.objects.get(name="Storage")
        acl_resource_type, created = ResourceType.objects.get_or_create(name="ACL")

        Resource.objects.get_or_create(
            resource_type=storage_resource_type,
            parent_resource=None,
            name="Storage2",
            description="Storage allocation via Qumulo",
            is_available=True,
            is_public=True,
            is_allocatable=True,
            requires_payment=True,
        )

        Resource.objects.get_or_create(
            name="rw",
            description="RW ACL",
            resource_type=acl_resource_type,
            is_available=True,
            is_public=False,
            is_allocatable=True,
            requires_payment=False,
        )

        Resource.objects.get_or_create(
            name="ro",
            description="RO ACL",
            resource_type=acl_resource_type,
            is_available=True,
            is_public=False,
            is_allocatable=True,
            requires_payment=False,
        )
