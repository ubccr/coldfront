from coldfront.core.allocation.models import AllocationAttributeType, AttributeType, AllocationLinkage, Allocation

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        # jprew - NOTE - adding new flags to these get_or_create
        # calls results in the creation of *new* AllocationAttributeType objects
        # which will lead to errors when finding them by name

        print("Adding Missing Allocation Linkages")

        parent_to_children_map = {
            "1": ["4"],
            '16': ["19"],
        }

        for parent, children in parent_to_children_map.items():
            parent_allocation = Allocation.objects.get(pk=parent)
            linkage, _ = AllocationLinkage.objects.get_or_create(
                parent=parent_allocation
            )
            for child in children:
                linkage.children.add(Allocation.objects.get(pk=child))
            linkage.save()
