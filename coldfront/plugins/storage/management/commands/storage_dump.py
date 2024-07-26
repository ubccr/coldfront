import logging
from django.core.management.base import BaseCommand
from coldfront.core.allocation.models import (
    Allocation, AllocationAttribute, AllocationStatusChoice
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Export storage quotas for allocations to a file or console.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output_file',
            type=str,
            help='The file to write the storage quotas to. If not provided, output will be printed to the console.'
        )

    def handle(self, *args, **kwargs):
        output_file = kwargs.get('output_file')

        # Fetch all allocations
        allocations = Allocation.objects.all()
        self.stdout.write(self.style.SUCCESS(f'Found {allocations.count()} allocations.'))

        if allocations.count() == 0:
            self.stdout.write(self.style.WARNING('No allocations found in the database.'))
            return

        output = []
        for allocation in allocations:
            self.stdout.write(self.style.SUCCESS(f'Processing allocation ID: {allocation.id}'))
            
            attributes = AllocationAttribute.objects.filter(allocation=allocation)
            attr_dict = {attr.allocation_attribute_type.name: attr.value for attr in attributes}

            self.stdout.write(self.style.SUCCESS(f'Attributes for allocation {allocation.id}: {attr_dict}'))

            storage_group_name_key = 'Storage_Group_Name'
            storage_quota_keys = ['Storage Quota (GB)', 'Storage Quota (TB)']
            
            # Get resource type
            resource_types = [resource.name for resource in allocation.resources.all()]
            status_name = allocation.status.name if allocation.status else 'Unknown'

            if (storage_group_name_key in attr_dict and 
                any(key in attr_dict for key in storage_quota_keys)):

                storage_group_name = attr_dict[storage_group_name_key]

                if 'Storage Quota (GB)' in attr_dict:
                    quota = attr_dict['Storage Quota (GB)']
                    unit = 'GB'
                elif 'Storage Quota (TB)' in attr_dict:
                    quota = float(attr_dict['Storage Quota (TB)']) * 1024  # Convert TB to GB
                    unit = 'TB'
                else:
                    self.stdout.write(self.style.ERROR(f'No valid storage quota found for allocation ID: {allocation.id}'))
                    continue

                # Convert quota to GB if needed
                quota_gb = float(quota) if unit == 'GB' else quota
                for resource_type in resource_types:
                    output.append(f'{resource_type}|{storage_group_name}|{int(quota_gb)}|{status_name}')
                    self.stdout.write(self.style.SUCCESS(f'Prepared quota: {quota_gb} GB for storage group: {storage_group_name}, Status: {status_name}'))

        if output_file:
            with open(output_file, 'w') as file:
                file.write('\n'.join(output))
            self.stdout.write(self.style.SUCCESS(f'Storage quotas successfully exported to {output_file}'))
        else:
            # Print the output to the console
            if output:
                self.stdout.write(self.style.SUCCESS('\n'.join(output)))
            else:
                self.stdout.write(self.style.WARNING('No data to export.'))
