from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource


class Command(BaseCommand):

    help = 'Verify that data loaded into the LRC service are correct.'

    def handle(self, *args, **options):
        self.assert_projects_have_pis()
        self.assert_user_profile_is_pi_consistent_with_project_pis()
        self.assert_pis_renewed_at_most_one_pca()
        self.assert_departmental_project_allocation_values()

    def assert_departmental_project_allocation_values(self):
        allocation_by_resource = {}
        departmental_compute_resources = Resource.objects.filter(
            Q(name__endswith=' Compute'), ~Q(name__startswith='LAWRENCIUM'))
        for resource in departmental_compute_resources:
            allocations = Allocation.objects.filter(resources=resource)
            num_allocations = allocations.count()
            if num_allocations == 0:
                message = (
                    f'There is no Allocation to Resource "{resource.name}".')
                self._write_warning(message)
                continue
            if num_allocations > 1:
                allocations_str = ', '.join([a.pk for a in allocations])
                message = (
                    f'There is more than one Allocation ({allocations_str}) '
                    f'to Resource "{resource.name}".')
                self._write_error(message)
            allocation_by_resource[resource] = allocations.first()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')

        for resource, allocation in allocation_by_resource.items():
            descriptor = (
                f'Allocation {allocation.pk} to Resource "{resource.name}"')

            # The Allocation should have Active status.
            if allocation.status.name != 'Active':
                message = (
                    f'{descriptor} unexpectedly has status '
                    f'"{allocation.status.name}".')
                self._write_error(message)

            # The Allocation should not have a start or end date.
            for date_field_name in ('start_date', 'end_date'):
                date_field = getattr(allocation, date_field_name)
                if date_field is not None:
                    message = (
                        f'{descriptor} unexpectedly has a {date_field_name}.')
                    self._write_error(message)

            # The Allocation should have the maximum number of Service Units.
            allocation_attribute = AllocationAttribute.objects.filter(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation).first()
            if allocation_attribute is None:
                message = f'{descriptor} has no "Service Units" attribute.'
                self._write_error(message)
            if allocation_attribute.value != str(settings.ALLOCATION_MAX):
                message = (
                    f'{descriptor} unexpectedly does not have '
                    f'{settings.ALLOCATION_MAX} service units.')
                self._write_error(message)

            for allocation_user in allocation.allocationuser_set.iterator():
                descriptor = (
                    f'AllocationUser {allocation_user.pk} on Allocation '
                    f'{allocation.pk} to Resource "{resource.name}"')

                # Each AllocationUser should have Active status.
                if allocation_user.status.name != 'Active':
                    message = (
                        f'{descriptor} unexpectedly has status '
                        f'"{allocation_user.status.name}".')
                    self._write_error(message)

                # Each AllocationUser should have the maximum number of Service
                # Units.
                allocation_user_attribute = \
                    AllocationUserAttribute.objects.filter(
                        allocation_attribute_type=allocation_attribute_type,
                        allocation_user=allocation_user).first()
                if allocation_user_attribute is None:
                    message = (
                        f'{descriptor} has no "Service Units" attribute.')
                    self._write_error(message)
                if (allocation_user_attribute.value !=
                        str(settings.ALLOCATION_MAX)):
                    message = (
                        f'{descriptor} unexpectedly does not have '
                        f'{settings.ALLOCATION_MAX} service units.')
                    self._write_error(message)

    def assert_user_profile_is_pi_consistent_with_project_pis(self):
        user_pks_with_pi_status = set(
            User.objects.filter(userprofile__is_pi=True).values_list(
                'pk', flat=True))
        seen_users = set()

        project_users = ProjectUser.objects.filter(
            role__name='Principal Investigator')
        for project_user in project_users.iterator():
            user_pk = project_user.user.pk
            if user_pk in seen_users:
                continue
            if user_pk in user_pks_with_pi_status:
                user_pks_with_pi_status.remove(user_pk)
                seen_users.add(user_pk)
                continue
            message = (
                f'ProjectUser {project_user.pk} is a PI, but the User does '
                f'not have is_pi status.')
            self._write_error(message)

        if user_pks_with_pi_status:
            message = (
                f'Users {sorted(user_pks_with_pi_status)} have is_pi status, '
                f'but are not PIs of Projects.')
            self._write_error(message)

    def assert_projects_have_pis(self):
        for project in Project.objects.iterator():
            if not project.pis().exists():
                message = f'Project {project.name} has no PIs.'
                self._write_error(message)

    def assert_pis_renewed_at_most_one_pca(self):
        allocation_period = AllocationPeriod.objects.get(
            name='Allowance Year 2022 - 2023')
        computing_allowance = Resource.objects.get(
            name='PI Computing Allowance')
        for pi in User.objects.filter(userprofile__is_pi=True).iterator():
            non_denied_requests = AllocationRenewalRequest.objects.filter(
                Q(pi=pi),
                Q(computing_allowance=computing_allowance),
                Q(allocation_period=allocation_period),
                ~Q(status__name='Denied'))
            if non_denied_requests.count() > 1:
                requests_str = ', '.join(
                    non_denied_requests.values_list('pk', flat=True))
                message = (
                    f'User {pi.username} ({pi.pk}) has multiple non-Denied '
                    f'renewal requests: {requests_str}.')
                self._write_error(message)

    def _write_error(self, message):
        self.stderr.write(self.style.ERROR(message))

    def _write_warning(self, message):
        self.stdout.write(self.style.WARNING(message))
