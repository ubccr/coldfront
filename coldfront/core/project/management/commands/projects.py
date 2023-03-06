from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import is_primary_cluster_project
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import DropEmailStrategy

import logging


"""An admin command for managing projects."""


class Command(BaseCommand):

    help = 'Manage projects.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self._add_create_subparser(subparsers)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        if subcommand == 'create':
            self._handle_create(*args, **options)

    @staticmethod
    def _add_create_subparser(parsers):
        """Add a subparser for the 'create' subcommand."""
        parser = parsers.add_parser(
            'create',
            help=(
                'Create a project with an allocation to a particular compute '
                'resource. Note: The current use case for this is to create a '
                'project for a newly-created standalone cluster. It cannot be '
                'used to create projects under the primary cluster (e.g., '
                'Savio on BRC, Lawrencium on LRC), under a standalone '
                'cluster that (a) can have at most one project and (b) '
                'already has a project, or, for BRC, under the Vector '
                'project.'))
        parser.add_argument(
            'name', help='The name of the project to create.', type=str)
        parser.add_argument(
            'cluster_name',
            help=(
                'The name of a cluster, for which a compute resource (e.g., '
                '"{cluster_name} Compute") should exist.'))
        parser.add_argument(
            'pi_usernames',
            help=(
                'A space-separated list of usernames of users to make the '
                'project\'s PIs.'),
            nargs='+',
            type=str)
        add_argparse_dry_run_argument(parser)

    @staticmethod
    def _create_project_with_compute_allocation_and_pis(project_name,
                                                        compute_resource,
                                                        pi_users):
        """Create a Project with the given name, with an Allocation to
        the given compute Resource, and with the given Users as
        Principal Investigators. Return the Project.

        Some fields are set by default:
            - The Project's status is 'Active'.
            - The ProjectUsers' statuses are 'Active'.
            - The Allocation's status is 'Active'.
            - The Allocation's start_date is today.
            - The Allocation's end_date is None.
            - The Allocation has the maximum number of service units.

        TODO: When the command is generalized, allow these to be
         specified.
        """
        with transaction.atomic():
            project = Project.objects.create(
                name=project_name,
                title=project_name,
                status=ProjectStatusChoice.objects.get(name='Active'))

            project_users = []
            for pi_user in pi_users:
                project_user = ProjectUser.objects.create(
                    project=project,
                    user=pi_user,
                    role=ProjectUserRoleChoice.objects.get(
                        name='Principal Investigator'),
                    status=ProjectUserStatusChoice.objects.get(name='Active'))
                project_users.append(project_user)

            allocation = Allocation.objects.create(
                project=project,
                status=AllocationStatusChoice.objects.get(name='Active'),
                start_date=display_time_zone_current_date(),
                end_date=None)
            allocation.resources.add(compute_resource)

            num_service_units = settings.ALLOCATION_MAX
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name='Service Units'),
                allocation=allocation,
                value=str(num_service_units))

            ProjectTransaction.objects.create(
                project=project,
                date_time=utc_now_offset_aware(),
                allocation=num_service_units)

            runner_factory = NewProjectUserRunnerFactory()
            for project_user in project_users:
                runner = runner_factory.get_runner(
                    project_user, NewProjectUserSource.AUTO_ADDED,
                    email_strategy=DropEmailStrategy())
                runner.run()

            for pi_user in pi_users:
                pi_user.userprofile.is_pi = True
                pi_user.userprofile.save()

        return project

    def _handle_create(self, *args, **options):
        """Handle the 'create' subcommand."""
        cleaned_options = self._validate_create_options(options)
        project_name = cleaned_options['project_name']
        compute_resource = cleaned_options['compute_resource']
        pi_users = cleaned_options['pi_users']

        pi_users_str = (
            '[' +
            ', '.join(f'"{pi_user.username}"' for pi_user in pi_users) +
            ']')
        message_template = (
            f'{{0}} Project "{project_name}" with Allocation to '
            f'"{compute_resource.name}" Resource under PIs {pi_users_str}.')
        if options['dry_run']:
            message = message_template.format('Would create')
            self.stdout.write(self.style.WARNING(message))
            return

        try:
            self._create_project_with_compute_allocation_and_pis(
                project_name, compute_resource, pi_users)
        except Exception as e:
            message = message_template.format('Failed to create')
            self.stderr.write(self.style.ERROR(message))
            self.logger.exception(f'{message}\n{e}')
        else:
            message = message_template.format('Created')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    @staticmethod
    def _validate_create_options(options):
        """Validate the options provided to the 'create' subcommand.
        Raise a subcommand if any are invalid or if they violate
        business logic, else return a dict of the form:
            {
                'project_name': 'project_name',
                'compute_resource': Resource,
                'pi_users': list of Users,
            }
        """
        project_name = options['name'].lower()
        if Project.objects.filter(name=project_name).exists():
            raise CommandError(
                f'A Project with name "{project_name}" already exists.')

        cluster_name = options['cluster_name']
        lowercase_cluster_name = cluster_name.lower()
        uppercase_cluster_name = cluster_name.upper()

        # TODO: When the command is generalized, enforce business logic re:
        #  the number of certain projects a PI may have.
        pi_usernames = list(set(options['pi_usernames']))
        pi_users = []
        for pi_username in pi_usernames:
            try:
                pi_user = User.objects.get(username=pi_username)
            except User.DoesNotExist:
                raise CommandError(
                    f'User with username "{pi_username}" does not exist.')
            else:
                pi_users.append(pi_user)

        lowercase_primary_cluster_name = get_primary_compute_resource_name(
            ).replace(' Compute', '').lower()
        is_cluster_primary = (
            lowercase_cluster_name == lowercase_primary_cluster_name)
        if (is_primary_cluster_project(Project(name=project_name)) or
                is_cluster_primary):
            raise CommandError(
                'This command may not be used to create a Project under the '
                'primary cluster.')

        # On BRC, also prevent a project from being created for the Vector
        # cluster.
        if flag_enabled('BRC_ONLY'):
            # TODO: As noted in the add_accounting_defaults management command,
            #  'Vector' should be fully-uppercase in its Resource name. Update
            #  this when that is the case.
            capitalized_cluster_name = cluster_name.capitalize()
            if capitalized_cluster_name == 'Vector':
                raise CommandError(
                    f'This command may not be used to create a Project under '
                    f'the {uppercase_cluster_name} cluster.')

        try:
            compute_resource = Resource.objects.get(
                name=f'{uppercase_cluster_name} Compute')
        except Resource.DoesNotExist:
            raise CommandError(
                f'Cluster {uppercase_cluster_name} does not exist.')

        # TODO: When the command is generalized, allow the project name to
        #  differ from the cluster name (within expected bounds).
        if project_name != lowercase_cluster_name:
            raise CommandError(
                f'This command may not be used to create a Project whose name '
                f'differs from the cluster name.')

        return {
            'project_name': project_name,
            'compute_resource': compute_resource,
            'pi_users': pi_users,
        }
