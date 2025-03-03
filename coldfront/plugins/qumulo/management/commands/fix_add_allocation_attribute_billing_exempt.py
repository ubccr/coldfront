from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand, CommandError
from coldfront.core.utils.validate import AttributeValidator
from coldfront.core.allocation.models import (
    AllocationAttributeType,
    Allocation,
    AllocationAttribute,
)


class Command(BaseCommand):
    help = """
        Run this command will ensure the required allocation attribute billing_exempt in each allocations.
        The default value is "Yes" or "No", and case-sensitive.
    """

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-d",
            "--default_value",
            default="No",
            type=str,
            help="modify the default value of billing_exempt",
        )

    def _validate_adding_billing_exempt(self):
        has_billing_exempt = False
        has_exempt = False

        try:
            AllocationAttributeType.objects.get(name="billing_exempt")
            has_billing_exempt = True
            AllocationAttributeType.objects.get(name="exempt")
            has_exempt = True
            if has_billing_exempt and has_exempt:
                raise ValidationError(
                    self.style.ERROR(
                        """
                        Allocation Attribute Types conflict: Require AppEng to migrate exempt to billing_exempt.
                            1. Copy the value of allocation_attirbute exempt to billing_exempt for all allocations
                            2. Delete the allocation_attribute exempt from all allocations.
                            3. Delete the allocation_attribute_type exempt.
                        """
                    )
                )

        except ObjectDoesNotExist:
            if not has_billing_exempt:
                raise ValidationError(
                    self.style.ERROR(
                        "Allocation Attribute Type missing: Run coldfront command 'add_qumulo_allocation_attribute_type'."
                    )
                )
            else:  # not has_exempt:
                self.stdout.write(
                    self.style.SUCCESS(
                        "[Info] Validation Pass: The system is ready for adding billing_exempt to pre-existing allocations."
                    )
                )

    def _add_billing_exempt(self):
        alloc_attr_type = AllocationAttributeType.objects.get(name="billing_exempt")
        allocations = Allocation.objects.filter(resources__name="Storage2")
        for allocation in allocations:
            try:
                AllocationAttribute.objects.get(
                    allocation_attribute_type=alloc_attr_type,
                    allocation=allocation,
                )
            except ObjectDoesNotExist:
                allocation_attribute = AllocationAttribute(
                    allocation_attribute_type=alloc_attr_type,
                    allocation=allocation,
                    value=self.default_value,
                )
                allocation_attribute.save()
                self.counter += 1
            except Exception as e:
                raise CommandError(
                    self.style.ERROR(f"Failed to add billing_exempt: {e}")
                )

    def handle(self, *args, **options) -> None:
        self.default_value = options["default_value"]
        self.counter = 0

        attr_validator = AttributeValidator(self.default_value)
        try:
            attr_validator.validate_yes_no()
            self._validate_adding_billing_exempt()
            self._add_billing_exempt()
            self.stdout.write(
                self.style.SUCCESS(
                    f"[Info] Successfully added {self.counter} billing_exempt as an allocation attribute to pre-existing allocations."
                )
            )
        except CommandError as e:
            self.stdout.write(self.style.ERROR(f"[Error] Failed: {e}"))
        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f"[Error] Invalid: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[Error] {e}"))
