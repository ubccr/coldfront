import json
import logging

from decimal import Decimal

from django.core.management.base import BaseCommand

from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.utils_.accounting_utils import set_job_amount
from coldfront.core.statistics.utils_.accounting_utils import validate_job_dates
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterfaceError
from coldfront.core.utils.common import add_argparse_dry_run_argument


"""An admin command for listing and updating jobs under free QoSes that
have non-zero amounts."""


class Command(BaseCommand):

    help = (
        'Manage jobs under free QoSes that have non-zero service unit amounts. '
        'List statistics about them or reset their amounts to zero, updating '
        'the associated usages.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self._add_reset_subparser(subparsers)
        self._add_summary_subparser(subparsers)
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        subcommand = options['subcommand']
        if subcommand == 'reset':
            self._handle_reset(*args, **options)
        elif subcommand == 'summary':
            self._handle_summary(*args, **options)

    @staticmethod
    def _add_reset_subparser(parsers):
        """Add a subparser for the 'reset' subcommand."""
        parser = parsers.add_parser(
            'reset',
            help=(
                 'Set amounts for relevant jobs to zero, and update associated '
                 'usages.'))
        parser.add_argument(
            'qos_names',
            help='A space-separated list of free QoS names.',
            nargs='+',
            type=str)
        parser.add_argument(
            '--project',
            help='The name of a specific project to perform the reset for.',
            type=str)
        add_argparse_dry_run_argument(parser)

    @staticmethod
    def _add_summary_subparser(parsers):
        """Add a subparser for the 'summary' subcommand."""
        parser = parsers.add_parser(
            'summary', help='Get a JSON summary of relevant jobs.')
        parser.add_argument(
            'qos_names',
            help='A space-separated list of free QoS names.',
            nargs='+',
            type=str)
        parser.add_argument(
            '--project',
            help='The name of a specific project to get a summary for.',
            type=str)

    def _handle_reset(self, *args, **options):
        """Handle the 'reset' subcommand."""
        if options['project'] is not None:
            project = Project.objects.get(name=options['project'])
        else:
            project = None
        self._zero_out_free_qos_jobs(
            options['qos_names'], project=project, dry_run=options['dry_run'])

    def _handle_summary(self, *args, **options):
        """Handle the 'summary' subcommand."""
        if options['project'] is not None:
            project = Project.objects.get(name=options['project'])
        else:
            project = None
        output_json = self._summary_json(options['qos_names'], project=project)
        self.stdout.write(json.dumps(output_json, indent=4, sort_keys=True))

    @staticmethod
    def _summary_json(qos_names, project=None):
        """Return a dictionary detailing the number of jobs with the
        given QoSes that have non-zero amounts, as well as the total
        associated usage. Optionally only consider jobs under the given
        Project. """
        zero = Decimal('0.00')

        num_jobs = 0
        total_by_project_id = {}
        kwargs = {
            'qos__in': qos_names,
            'amount__gt': zero,
        }
        if project is not None:
            kwargs['accountid'] = project
        for job in Job.objects.filter(**kwargs).iterator():
            num_jobs += 1
            # Use accountid_id to avoid a foreign key lookup.
            project_id = job.accountid_id
            if project_id not in total_by_project_id:
                total_by_project_id[project_id] = zero
            total_by_project_id[project_id] += job.amount

        total_by_project_name = {}
        total_by_allowance = {}
        for project_id, amount in total_by_project_id.items():
            project = Project.objects.get(id=project_id)
            total_by_project_name[project.name] = str(amount)
            if '_' in project.name:
                allowance_type = project.name.split('_')[0]
            else:
                allowance_type = project.name
            if allowance_type not in total_by_allowance:
                total_by_allowance[allowance_type] = zero
            total_by_allowance[allowance_type] += amount

        for allowance_name, amount in total_by_allowance.items():
            total_by_allowance[allowance_name] = str(amount)

        return {
            'num_jobs': num_jobs,
            'total_by_allowance': total_by_allowance,
            'total_by_project': total_by_project_name,
        }

    def _zero_out_free_qos_jobs(self, qos_names, project=None, dry_run=False):
        """For each job with one of the given QoSes, reset the job's
        amount to zero, and update the associated usages if
        appropriate. Optionally only consider jobs under the given
        Project. Optionally display updates instead of performing
        them."""
        computing_allowance_interface = ComputingAllowanceInterface()
        periodic_project_name_prefixes = tuple([
            computing_allowance_interface.code_from_name(allowance.name)
            for allowance in computing_allowance_interface.allowances()
            if ComputingAllowance(allowance).is_periodic()])

        total_by_project_name = {}
        project_cache = {}
        allocation_cache = {}

        zero = Decimal('0.00')
        num_jobs = 0
        kwargs = {
            'qos__in': qos_names,
            'amount__gt': zero,
        }
        if project is not None:
            kwargs['accountid'] = project
        for job in Job.objects.filter(**kwargs).iterator():
            num_jobs += 1
            jobslurmid = job.jobslurmid

            project_id = job.accountid_id
            if project_id in project_cache:
                project = project_cache[project_id]
            else:
                project = job.accountid
                project_cache[project_id] = project

            # Skip updating usages for any job that is outside its allocation's
            # allowance period. Some projects don't have meaningful periods;
            # avoid expensive lookups for them.
            try:
                computing_allowance_interface.allowance_from_project(project)
            except ComputingAllowanceInterfaceError:
                # Non-primary cluster project --> no allowance period
                update_usages = True
            else:
                if project.name.startswith(periodic_project_name_prefixes):
                    # Has a periodic allowance --> defined allowance period
                    # Only update usages if the job is within the current
                    # period.
                    if project_id in allocation_cache:
                        allocation = allocation_cache[project_id]
                    else:
                        allocation = get_project_compute_allocation(project)
                        allocation_cache[project_id] = allocation
                    job_data = job.__dict__
                    job_data['accountid'] = project
                    update_usages = validate_job_dates(
                        job_data, allocation, end_date_expected=True)
                else:
                    # Does not have a periodic allowance --> no allowance period
                    update_usages = True

            if project.name not in total_by_project_name:
                total_by_project_name[project.name] = {
                    'num_jobs': 0,
                    'usage': zero,
                }
            total_by_project_name[project.name]['num_jobs'] += 1
            if update_usages:
                total_by_project_name[project.name]['usage'] += job.amount
            else:
                message = (
                    f'Job {jobslurmid} outside of allowance period. Skipping '
                    f'usage update.')
                self.stdout.write(self.style.WARNING(message))

            if not dry_run:
                try:
                    set_job_amount(
                        jobslurmid, zero, update_usages=update_usages)
                except Exception as e:
                    self.logger.exception(e)
                    message = (
                        f'Failed to update amount for Job {jobslurmid}. '
                        f'Details:\n{e}')
                    self.stderr.write(self.style.ERROR(message))

        for project_name in total_by_project_name:
            usage_str = str(
                total_by_project_name[project_name]['usage'])
            total_by_project_name[project_name]['usage'] = usage_str
        result_json = json.dumps(
            total_by_project_name, indent=4, sort_keys=True)

        message = (
            f'Corrected amounts for {num_jobs} jobs under free QoSes '
            f'{", ".join(sorted(qos_names))} to zero and associated usages. '
            f'Summary:\n{result_json}')
        self.stdout.write(message)

        if not dry_run:
            compact_result_json = json.dumps(
                total_by_project_name, sort_keys=True)
            self.logger.info(
                f'Corrected amounts for {num_jobs} jobs under free QoSes '
                f'{", ".join(sorted(qos_names))} to zero and associated '
                f'usages. Summary: {compact_result_json}')
