from coldfront.core.project.models import ProjectAttributeType, AttributeType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Adding Qumulo Project Attribute Types")
        # add a department_number at the project level that is *not* used for direct billing
        # could maybe have it default for Allocation?
        # NOTE - there is no UserAttributeType collection, so this is a more natural spot
        ProjectAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name="Text"),
            name="sponsor_department_number",
            is_required=True,
            is_private=False,
            is_unique=False,
            is_changeable=True,
        )

        # NOTE: we'll keep "regular" allocations (even condo allocations) in "regular"
        # projects; a condo_group project is a special thing that lets us check the
        # sum of its allocations and bill them differently
        ProjectAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name="Yes/No"),
            name="is_condo_group",
            is_required=True,
            is_private=False,
            is_unique=False,
            is_changeable=True,
        )

        ProjectAttributeType.objects.get_or_create(
            attribute_type=AttributeType.objects.get(name="Yes/No"),
            name="allow_nonfaculty",
            is_required=True,
            is_private=False,
            is_unique=False,
            is_changeable=True,
        )
