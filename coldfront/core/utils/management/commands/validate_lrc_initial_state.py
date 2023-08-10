from decimal import Decimal

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
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.utils_.host_user_utils import is_lbl_employee


class Command(BaseCommand):

    help = 'Verify that data loaded into the LRC service are correct.'

    def handle(self, *args, **options):
        self.assert_projects_have_pis()
        self.assert_user_profile_is_pi_consistent_with_project_pis()
        self.assert_pis_renewed_at_most_one_pca()
        self.assert_pis_are_lbl_employees()
        self.assert_pca_project_allocation_values()
        self.assert_condo_and_recharge_project_allocation_values()
        self.assert_departmental_project_allocation_values()

    def assert_condo_and_recharge_project_allocation_values(self):
        lawrencium_compute_resource = Resource.objects.get(
            name='LAWRENCIUM Compute')
        computing_allowance_interface = ComputingAllowanceInterface()
        for resource_name in ('Condo Allocation', 'Recharge Allocation'):
            prefix = computing_allowance_interface.code_from_name(
                resource_name)
            for project in Project.objects.filter(
                    name__startswith=prefix).iterator():
                # The Project should have Active status.
                self._assert_project_status(project, 'Active')
                # The Project's ProjectUsers should have the correct values.
                for project_user in project.projectuser_set.iterator():
                    # Each ProjectUser should have Active status.
                    self._assert_project_user_status(project_user, 'Active')
                # The Project should have an Allocation to LAWRENCIUM Compute.
                allocation = Allocation.objects.filter(
                    project=project,
                    resources=lawrencium_compute_resource).first()
                if allocation is None:
                    message = (
                        f'Project {project.name} ({project.pk}) does not have '
                        f'an Allocation to Resource '
                        f'"{lawrencium_compute_resource.name}".')
                    self._write_error(message)
                    continue
                # The Allocation should have Active status.
                self._assert_allocation_status(allocation, 'Active')
                # The Allocation should have a start date, but no end date.
                self._assert_allocation_start_date_non_null(allocation)
                self._assert_allocation_end_date(allocation, None)
                # The Allocation should have the maximum number of Service
                # Units.
                self._assert_allocation_num_service_units(
                    allocation, settings.ALLOCATION_MAX)
                # The Allocation's AllocationUsers should have the correct
                # values.
                for allocation_user in \
                        allocation.allocationuser_set.iterator():
                    # Each AllocationUser should have Active status.
                    self._assert_allocation_user_status(
                        allocation_user, 'Active')
                    # Each AllocationUser should have the same number of
                    # Service Units as the Allocation.
                    self._assert_allocation_user_num_service_units(
                        allocation_user, settings.ALLOCATION_MAX)

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
                continue
            allocation_by_resource[resource] = allocations.first()

        for resource, allocation in allocation_by_resource.items():
            project = allocation.project
            # The Project should have Active status.
            self._assert_project_status(project, 'Active')
            # The Project's ProjectUsers should have the correct values.
            for project_user in project.projectuser_set.iterator():
                # Each ProjectUser should have Active status.
                self._assert_project_user_status(project_user, 'Active')
            # The Allocation should have Active status.
            self._assert_allocation_status(allocation, 'Active')
            # The Allocation should not have a start or end date.
            self._assert_allocation_start_date(allocation, None)
            self._assert_allocation_end_date(allocation, None)
            # The Allocation should have the maximum number of Service Units.
            self._assert_allocation_num_service_units(
                allocation, settings.ALLOCATION_MAX)
            # The Allocation's AllocationUsers should have the correct values.
            for allocation_user in allocation.allocationuser_set.iterator():
                # Each AllocationUser should have Active status.
                self._assert_allocation_user_status(allocation_user, 'Active')
                # Each AllocationUser should have the same number of Service
                # Units as the Allocation.
                self._assert_allocation_user_num_service_units(
                    allocation_user, settings.ALLOCATION_MAX)

    def assert_pis_are_lbl_employees(self):
        for project_user in ProjectUser.objects.filter(
                role__name='Principal Investigator').iterator():
            user = project_user.user
            if not is_lbl_employee(user):
                message = (
                    f'User {user.username} ({user.pk}) is a PI of Project '
                    f'{project_user.project.name}, but is not an LBL '
                    f'employee.')
                self._write_error(message)

    def assert_pca_project_allocation_values(self):
        lawrencium_compute_resource = Resource.objects.get(
            name='LAWRENCIUM Compute')
        allocation_period = AllocationPeriod.objects.get(
            name='Allowance Year 2022 - 2023')
        computing_allowance = Resource.objects.get(
            name='PI Computing Allowance')

        computing_allowance_interface = ComputingAllowanceInterface()
        prefix = computing_allowance_interface.code_from_name(
            'PI Computing Allowance')
        num_service_units = Decimal(
            computing_allowance_interface.service_units_from_name(
                computing_allowance.name, is_timed=True,
                allocation_period=allocation_period))

        for project in Project.objects.filter(
                name__startswith=prefix).iterator():
            num_complete_requests = AllocationRenewalRequest.objects.filter(
                post_project=project,
                computing_allowance=computing_allowance,
                allocation_period=allocation_period,
                status__name='Complete').count()
            was_renewed = num_complete_requests > 0
            # The Project should have Active status if it was renewed, else
            # Inactive.
            self._assert_project_status(
                project, 'Active' if was_renewed else 'Inactive')
            # The Project's ProjectUsers should have the correct values.
            for project_user in project.projectuser_set.iterator():
                # Each ProjectUser should have Active status.
                self._assert_project_user_status(project_user, 'Active')
            # The Project should have an Allocation to LAWRENCIUM Compute.
            allocation = Allocation.objects.filter(
                project=project,
                resources=lawrencium_compute_resource).first()
            if allocation is None:
                message = (
                    f'Project {project.name} ({project.pk}) does not have '
                    f'an Allocation to Resource '
                    f'"{lawrencium_compute_resource.name}".')
                self._write_error(message)
                continue
            # The Allocation should have Active status if it was renewed, else
            # Expired.
            self._assert_allocation_status(
                allocation, 'Active' if was_renewed else 'Expired')
            # The Allocation should have a start date greater than or equal to
            # the start of the AllocationPeriod. It should have an end date of
            # the end of the AllocationPeriod if it was renewed, else None.
            if allocation.start_date is None:
                message = (
                    f'Allocation {allocation.pk} unexpectedly has no '
                    f'start_date.')
                self._write_error(message)
            else:
                self._assert_allocation_start_date_gte(
                    allocation, allocation_period.start_date)
            self._assert_allocation_end_date(
                allocation,
                allocation_period.end_date if was_renewed else None)
            # The Allocation should have Service Units proportional to the
            # number of renewals under it.
            expected_num_service_units = (num_complete_requests *
                                          num_service_units)
            self._assert_allocation_num_service_units(
                allocation, expected_num_service_units)
            # The Allocation's AllocationUsers should have the correct values.
            for allocation_user in allocation.allocationuser_set.iterator():
                # Each AllocationUser should have Active status.
                self._assert_allocation_user_status(
                    allocation_user, 'Active')
                # Each AllocationUser should have the same number of Service
                # Units as the Allocation.
                self._assert_allocation_user_num_service_units(
                    allocation_user, expected_num_service_units)

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

    def _assert_allocation_end_date(self, allocation, expected_end_date):
        actual_end_date = allocation.end_date
        if actual_end_date != expected_end_date:
            message = (
                f'Allocation {allocation.pk} unexpectedly has end_date '
                f'{actual_end_date} instead of {expected_end_date}.')
            self._write_error(message)

    def _assert_allocation_num_service_units(self, allocation,
                                             expected_num_service_units):
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation).first()
        if allocation_attribute is None:
            message = (
                f'Allocation {allocation.pk} has no "Service Units" '
                f'attribute.')
            self._write_error(message)
        actual_num_service_units = allocation_attribute.value
        if actual_num_service_units != str(expected_num_service_units):
            message = (
                f'Allocation {allocation.pk} unexpectedly has '
                f'{actual_num_service_units} service units instead of '
                f'{expected_num_service_units}.')
            self._write_error(message)

    def _assert_allocation_start_date(self, allocation, expected_start_date):
        actual_start_date = allocation.start_date
        if actual_start_date != expected_start_date:
            message = (
                f'Allocation {allocation.pk} unexpectedly has start_date '
                f'{actual_start_date} instead of {expected_start_date}.')
            self._write_error(message)

    def _assert_allocation_start_date_gte(self, allocation, min_start_date):
        actual_start_date = allocation.start_date
        if actual_start_date < min_start_date:
            message = (
                f'Allocation {allocation.pk} unexpected has start_date '
                f'earlier than {min_start_date}.')
            self._write_error(message)

    def _assert_allocation_start_date_non_null(self, allocation):
        actual_start_date = allocation.start_date
        if actual_start_date is None:
            message = (
                f'Allocation {allocation.pk} unexpectedly has no start_date.')
            self._write_error(message)

    def _assert_allocation_status(self, allocation, expected_status_name):
        actual_status_name = allocation.status.name
        if actual_status_name != expected_status_name:
            message = (
                f'Allocation {allocation.pk} unexpectedly has status '
                f'{actual_status_name} instead of {expected_status_name}.')
            self._write_error(message)

    def _assert_allocation_user_num_service_units(self, allocation_user,
                                                  expected_num_service_units):
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=allocation_attribute_type,
            allocation_user=allocation_user).first()
        if allocation_user_attribute is None:
            message = (
                f'AllocationUser {allocation_user.pk} has no "Service Units" '
                f'attribute.')
            self._write_error(message)
            return
        actual_num_service_units = allocation_user_attribute.value
        if actual_num_service_units != str(expected_num_service_units):
            message = (
                f'AllocationUser {allocation_user.pk} unexpectedly has '
                f'{actual_num_service_units} service units instead of '
                f'{expected_num_service_units}.')
            self._write_error(message)

    def _assert_allocation_user_status(self, allocation_user,
                                       expected_status_name):
        actual_status_name = allocation_user.status.name
        if actual_status_name != expected_status_name:
            message = (
                f'AllocationUser {allocation_user.pk} unexpectedly has status '
                f'{actual_status_name} instead of {expected_status_name}.')
            self._write_error(message)

    def _assert_project_status(self, project, expected_status_name):
        actual_status_name = project.status.name
        if actual_status_name != expected_status_name:
            message = (
                f'Project {project.pk} unexpectedly has status '
                f'{actual_status_name} instead of {expected_status_name}.')
            self._write_error(message)

    def _assert_project_user_status(self, project_user, expected_status_name):
        actual_status_name = project_user.status.name
        if actual_status_name != expected_status_name:
            message = (
                f'ProjectUser {project_user.pk} unexpectedly has status '
                f'{actual_status_name} instead of {expected_status_name}.')
            self._write_error(message)

    def _write_error(self, message):
        self.stderr.write(self.style.ERROR(message))

    def _write_warning(self, message):
        self.stdout.write(self.style.WARNING(message))
