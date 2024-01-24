from decimal import Decimal

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils_.accounting_utils import allocate_service_units_to_user
from coldfront.core.project.models import Project
from coldfront.core.utils.common import add_argparse_dry_run_argument

import logging

"""An admin command that ensures that all users across all active
projects are allocated the same number of service units as the
project."""


class Command(BaseCommand):

    help = (
        'Across all active projects, ensure that the number of service '
        'units allocated to each user is equal to that of the project.')

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        for project in Project.objects.filter(status__name='Active'):
            self._handle_project(project, dry_run)

    def _handle_discrepant_user_attribute(self, project, user, allocation_user,
                                          allocation_user_attribute,
                                          num_service_units, dry_run):
        """Handle the case when the user's attribute does not match that
        of the project."""
        message_template = (
            f'{{0}} discrepant AllocationUserAttribute '
            f'({allocation_user_attribute.pk}) of type '
            f'"{self._allocation_attribute_type.name}" for ({project.name} '
            f'({project.pk}), {user.username} ({user.pk})) from value '
            f'{allocation_user_attribute.value} to {num_service_units}.')
        if dry_run:
            message = message_template.format('Would update')
            self.stdout.write(self.style.WARNING(message))
        else:
            allocate_service_units_to_user(allocation_user, num_service_units)
            message = message_template.format('Updated')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    def _handle_missing_user_attribute(self, project, user, allocation_user,
                                       num_service_units, dry_run):
        """Handle the case when the user has no attribute."""
        message_template = (
            f'{{0}} missing AllocationUserAttribute of type '
            f'"{self._allocation_attribute_type.name}" for ({project.name} '
            f'({project.pk}), {user.username} ({user.pk})) with '
            f'value {num_service_units}.')
        if dry_run:
            message = message_template.format('Would create')
            self.stdout.write(self.style.WARNING(message))
        else:
            allocate_service_units_to_user(allocation_user, num_service_units)
            message = message_template.format('Created')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    def _handle_project(self, project, dry_run):
        """Handle corrections for the given Project."""
        try:
            allocation = get_project_compute_allocation(project)
        except Allocation.DoesNotExist:
            message = f'Project {project.name} has no compute allocation.'
            self.stderr.write(self.style.ERROR(message))
            return
        try:
            allocation_attribute = AllocationAttribute.objects.get(
                allocation_attribute_type=self._allocation_attribute_type,
                allocation=allocation)
        except AllocationAttribute.DoesNotExist:
            message = f'Project {project.name} does not have service units.'
            self.stderr.write(self.style.ERROR(message))
            return
        allocation_service_units = Decimal(allocation_attribute.value)

        for allocation_user in allocation.allocationuser_set.all():
            user = allocation_user.user

            # If the user does not have access to the cluster under the
            # allocation, the attribute may be missing or discrepant.
            has_cluster_access_under_allocation = \
                AllocationUserAttribute.objects.filter(
                    allocation_user=allocation_user,
                    allocation_attribute_type__name='Cluster Account Status',
                    value='Active').exists()
            if not has_cluster_access_under_allocation:
                continue

            try:
                allocation_user_attribute = \
                    allocation_user.allocationuserattribute_set.get(
                        allocation_attribute_type=
                        self._allocation_attribute_type)
            except AllocationUserAttribute.DoesNotExist:
                self._handle_missing_user_attribute(
                    project, user, allocation_user,
                    allocation_service_units, dry_run)
            else:
                allocation_user_service_units = Decimal(
                    allocation_user_attribute.value)
                if (allocation_user_service_units !=
                        allocation_service_units):
                    self._handle_discrepant_user_attribute(
                        project, user, allocation_user,
                        allocation_user_attribute, allocation_service_units,
                        dry_run)
