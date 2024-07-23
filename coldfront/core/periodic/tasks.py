import subprocess
from celery import shared_task
from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeUsage, AllocationAttributeType

@shared_task
def update_allocations_usage():
    print("Starting update_allocations_usage task...")

    # Find all allocation attribute types that are consumable and have a defined usage command
    consumable_attributes = AllocationAttributeType.objects.filter(
        has_usage=True, get_usage_command__isnull=False
    )
    print(f"Found {consumable_attributes.count()} consumable attributes with usage commands.")

    for attr_type in consumable_attributes:
        print(f"Processing attribute type: {attr_type.name}")

        # Find all AllocationAttributes that use this attribute type
        allocation_attributes = AllocationAttribute.objects.filter(
            allocation_attribute_type=attr_type
        )
        print(f"Found {allocation_attributes.count()} allocation attributes for type {attr_type.name}.")

        for allocation_attr in allocation_attributes:
            print(f"Processing allocation attribute ID: {allocation_attr.id}")

            # Find the associated Allocation object
            allocation = Allocation.objects.filter(
                pk=allocation_attr.pk  # Assumes there is a relationship between Allocation and AllocationAttribute
            ).first()

            if allocation:
                project = allocation.project
                print(f"Project for allocation attribute ID {allocation_attr.id}: {project}")
            else:
                print(f"Allocation not found for attribute ID {allocation_attr.id}")
                continue

            # Retrieve the value of the slurm_account_name associated with the allocation
            slurm_account_name_attr = AllocationAttribute.objects.filter(
                allocation_attribute_type__name='slurm_account_name',
                allocation=allocation
            ).first()

            if slurm_account_name_attr:
                slurm_account_name = slurm_account_name_attr.value
                print(f"Slurm account name for allocation ID {allocation_attr.id}: {slurm_account_name}")
            else:
                print(f"Slurm account name attribute not found for allocation ID {allocation_attr.id}")
                continue

            # Retrieve the command to execute
            command = attr_type.get_usage_command
            if command:
                # Replace "%SLURM_ACCOUNT_NAME%" in the command if present
                command = command.replace("%SLURM_ACCOUNT_NAME%", slurm_account_name)
                print(f"Executing command: {command}")

                try:
                    # Execute the command
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    print(f"Command output: {result.stdout}")

                    # Save the returned value as an integer in the database
                    usage_value = int(result.stdout.strip())
                    print(f"Parsed usage value: {usage_value}")

                    # Find or create an AllocationAttributeUsage object
                    usage, created = AllocationAttributeUsage.objects.get_or_create(
                        allocation_attribute=allocation_attr,
                        defaults={'value': usage_value}
                    )

                    if created:
                        print(f"Created new AllocationAttributeUsage for attribute ID {allocation_attr.id} with value {usage_value}")
                    else:
                        # Update the value if the object already exists
                        usage.value = usage_value
                        usage.save()
                        print(f"Updated AllocationAttributeUsage for attribute ID {allocation_attr.id} with new value {usage_value}")

                except Exception as e:
                    print(f"Error executing command: {e}")

    print("Finished update_allocations_usage task.")
