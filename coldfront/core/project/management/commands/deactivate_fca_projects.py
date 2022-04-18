from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from django.core.management.base import BaseCommand
from django.db.models import Q
import logging

"""An admin command that sets eligible FCA Projects to 'Inactive' and
their corresponding compute Allocations to 'Expired'."""


class Command(BaseCommand):

    help = (
        'Set eligible FCA Projects to \'Inactive\' and their corresponding '
        'compute Allocations to \'Expired\'. NOTE: As currently written, this '
        'command assumes a particular AllocationPeriod. It should not be run '
        'outside of that period.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run', action='store_true',
            help='Display updates without performing them.')

    def handle(self, *args, **options):
        """For each FCA Project that does not satisfy at least one of
        the following criteria, set its status to 'Inactive' and its
        compute Allocation's status to 'Expired':
            (a) The Project is the post_project of a non-denied
                AllocationRenewalRequest during the current
                AllocationPeriod,
            (b) The Project is the project of a non-denied
                SavioProjectAllocationRequest during the current
                AllocationPeriod."""
        allocation_period = get_current_allowance_year_period()
        # Retrieve IDs of projects with non-denied renewal requests.
        a = self.non_denied_fca_allocation_renewal_requests(allocation_period)
        a_ids = set(a.values_list('post_project', flat=True))
        # Retrieve IDs of projects with non-denied project requests.
        b = self.non_denied_fca_new_project_requests(allocation_period)
        b_ids = set(b.values_list('project', flat=True))

        ineligible_project_ids = set.union(a_ids, b_ids)
        eligible_projects = Project.objects.filter(
            Q(name__startswith='fc_') & ~Q(id__in=ineligible_project_ids))

        self.deactivate_projects(eligible_projects, options['dry_run'])

    def deactivate_projects(self, projects, dry_run):
        """Given a queryset of Projects, set each one's status to
        'Inactive' and set the status of the corresponding 'CLUSTER_NAME
        Compute' Allocation to 'Expired'.

        If dry_run is True, write the pair to stdout without creating
        the request."""
        project_status = ProjectStatusChoice.objects.get(name='Inactive')
        allocation_status = AllocationStatusChoice.objects.get(name='Expired')
        for project in projects:
            allocation = get_project_compute_allocation(project)
            if dry_run:
                message = (
                    f'Would update Project {project.name} ({project.pk})\'s '
                    f'status to {project_status.name} and Allocation '
                    f'{allocation.pk}\'s status to {allocation_status.name}.')
                self.stdout.write(self.style.WARNING(message))
                continue
            project.status = project_status
            project.save()
            allocation.status = allocation_status
            allocation.save()
            message = (
                f'Updated Project {project.name} ({project.pk})\'s status to '
                f'{project_status.name} and Allocation {allocation.pk}\'s '
                f'status to {allocation_status.name}.')
            self.logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))

    @staticmethod
    def non_denied_fca_new_project_requests(allocation_period):
        """Return a queryset of new project requests for FCAs under the
        given AllocationPeriod that are not denied."""
        status_names = list(
            ProjectAllocationRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        kwargs = {
            'allocation_period': allocation_period,
            'allocation_type': SavioProjectAllocationRequest.FCA,
            'status__name__in': status_names,
        }
        return SavioProjectAllocationRequest.objects.filter(**kwargs)

    @staticmethod
    def non_denied_fca_allocation_renewal_requests(allocation_period):
        """Return a queryset of allocation renewal requests for FCAs
        under the given AllocationPeriod that are not denied."""
        status_names = list(
            AllocationRenewalRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        kwargs = {
            'allocation_period': allocation_period,
            'post_project__name__startswith': (
                SavioProjectAllocationRequest.FCA),
            'status__name__in': status_names,
        }
        return AllocationRenewalRequest.objects.filter(**kwargs)
