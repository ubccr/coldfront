from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.resource.models import Resource

from django.core.management.base import BaseCommand

from coldfront.plugins.qumulo.views.allocation_view import AllocationView


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("allocation_pk", type=int)

    def handle(self, *args, **options):
        allocation_pk = options["allocation_pk"]

        print(f"Creating RO Access Allocation for {allocation_pk}")

        try:
            allocation = Allocation.objects.get(pk=allocation_pk)
        except Exception as e:
            print(f"Allocation with pk {allocation_pk} not found")
            return

        access_data = {"name": "RO Users", "resource": "ro", "users": []}

        access_allocation = AllocationView.create_access_allocation(
            access_data=access_data,
            project=allocation.project,
            storage_name=allocation.get_attribute(name="storage_name"),
            storage_allocation=allocation,
        )

        access_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        access_allocation.save()

        print(f"Access Allocation created for {allocation_pk}")
