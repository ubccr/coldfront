from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
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
                SavioProjectAllocationRequest.

        TODO: Once the first AllocationPeriod has ended, criterion (b)
        TODO: will need to be refined to filter on time.
        """
        # Retrieve IDs of projects with non-denied renewal requests.
        allocation_period = get_current_allowance_year_period()
        a = self.fca_projects_with_non_denied_renewal_requests(
            allocation_period)
        a_ids = set(a.values_list('post_project', flat=True))
        # Retrieve IDs of projects with non-denied project requests.
        b = self.fca_projects_with_non_denied_project_requests()
        b_ids = set(b.values_list('project', flat=True))

        ineligible_project_ids = set.union(a_ids, b_ids)
        eligible_projects = Project.objects.filter(
            Q(name__startswith='fc_') & ~Q(id__in=ineligible_project_ids))

        self.deactivate_projects(eligible_projects, options['dry_run'])

    def deactivate_projects(self, projects, dry_run):
        """Given a queryset of Projects, set each one's status to
        'Inactive' and set the status of the corresponding compute
        Allocation to 'Expired'.

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
    def fca_projects_with_non_denied_project_requests():
        """Return a queryset of FCA Projects that are the project on a
        non-denied SavioProjectAllocationRequest.

        TODO: Once the first AllocationPeriod has ended, this will need
        TODO: to be refined to filter on time.
        """
        status_names = [
            'Under Review', 'Approved - Processing', 'Approved - Complete']
        kwargs = {
            'allocation_type': SavioProjectAllocationRequest.FCA,
            'status__name__in': status_names,
        }
        return SavioProjectAllocationRequest.objects.filter(**kwargs)

    @staticmethod
    def fca_projects_with_non_denied_renewal_requests(allocation_period):
        """Return a queryset of FCA Projects that are the post_project
        on a non-denied AllocationRenewalRequest during the given
        AllocationPeriod."""
        status_names = ['Under Review', 'Approved', 'Complete']
        kwargs = {
            'allocation_period': allocation_period,
            'post_project__name__startswith': 'fc_',
            'status__name__in': status_names,
        }
        return AllocationRenewalRequest.objects.filter(**kwargs)
