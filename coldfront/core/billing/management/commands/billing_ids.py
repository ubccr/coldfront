import logging

from django.contrib.auth.models import User
from django.core.management import CommandError
from django.core.management.base import BaseCommand

from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.utils import ProjectBillingActivityManager
from coldfront.core.billing.utils import ProjectUserBillingActivityManager
from coldfront.core.billing.utils import UserBillingActivityManager
from coldfront.core.billing.utils.queries import get_billing_activity_from_full_id
from coldfront.core.billing.utils.queries import get_billing_id_usages
from coldfront.core.billing.utils.queries import get_or_create_billing_activity_from_full_id
from coldfront.core.billing.utils.queries import is_billing_id_well_formed
from coldfront.core.billing.utils.validation import is_billing_id_valid
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.utils.common import add_argparse_dry_run_argument


"""An admin command for creating and setting billing IDs."""


class Command(BaseCommand):

    help = 'Create and set billing IDs.'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self._add_create_subparser(subparsers)
        self._add_list_subparser(subparsers)
        self._add_set_subparser(subparsers)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'_handle_{subcommand}')
        handler(*args, **options)

    @staticmethod
    def _add_create_subparser(parsers):
        """Add a subparser for the 'create' subcommand."""
        parser = parsers.add_parser('create', help='Create a billing ID.')
        add_billing_id_argument(parser)
        add_ignore_invalid_argument(parser)
        add_argparse_dry_run_argument(parser)

    @staticmethod
    def _add_list_subparser(parsers):
        """Add a subparser for the 'list' command."""
        parser = parsers.add_parser(
            'list', help='List billing IDs matching filters.')
        add_billing_id_argument(parser, is_optional=True)
        add_project_name_argument(parser, is_optional=True)
        add_username_argument(parser, is_optional=True)

    @staticmethod
    def _add_set_subparser(parsers):
        """Add a subparser for the 'set' subcommand."""
        parser = parsers.add_parser(
            'set', help='Set a billing ID for a particular entity.')
        subparsers = parser.add_subparsers(
            dest='set_subcommand',
            help='The subcommand to run.',
            title='set_subcommands')
        subparsers.required = True

        project_default_parser = subparsers.add_parser(
            'project_default',
            help=(
                'Set the default billing ID for the Project with the given '
                'name.'))
        add_project_name_argument(project_default_parser)
        add_billing_id_argument(project_default_parser)
        add_ignore_invalid_argument(project_default_parser)
        add_argparse_dry_run_argument(project_default_parser)

        recharge_parser = subparsers.add_parser(
            'recharge',
            help=(
                'Set the billing ID to be used for the Recharge fee for the '
                'given User with the given user on the Project with the given '
                'name.'))
        add_project_name_argument(recharge_parser)
        add_username_argument(recharge_parser)
        add_billing_id_argument(recharge_parser)
        add_ignore_invalid_argument(recharge_parser)
        add_argparse_dry_run_argument(recharge_parser)

        user_account_parser = subparsers.add_parser(
            'user_account',
            help=(
                'Set the billing ID to tbe used for the user account fee for '
                'the User with the given username.'))
        add_username_argument(user_account_parser)
        add_billing_id_argument(user_account_parser)
        add_ignore_invalid_argument(user_account_parser)
        add_argparse_dry_run_argument(user_account_parser)

    @staticmethod
    def _get_billing_activity_or_error(full_id):
        """Return the BillingActivity corresponding to the given
        fully-formed billing ID, if it exists, else raise a
        CommandError."""
        if not is_billing_id_well_formed(full_id):
            raise CommandError(f'Billing ID {full_id} is malformed.')
        billing_activity = get_billing_activity_from_full_id(full_id)
        if not isinstance(billing_activity, BillingActivity):
            raise CommandError(f'Billing ID {full_id} does not exist.')
        return billing_activity

    @staticmethod
    def _get_project_or_error(project_name):
        """Return the Project with the given name, if it exists, else
        raise a CommandError."""
        try:
            return Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            raise CommandError(
                f'Project with name "{project_name}" does not exist.')

    @staticmethod
    def _get_project_user_or_error(project, user):
        """Return the ProjectUser associated with the given Project and
        User, if it exists, else raise a CommandError."""
        try:
            return ProjectUser.objects.get(project=project, user=user)
        except ProjectUser.DoesNotExist:
            raise CommandError(
                f'ProjectUser for Project {project.name} and User '
                f'{user.username} does not exist.')

    @staticmethod
    def _get_user_or_error(username):
        """Return the User with the given username, if it exists, else
        raise a CommandError."""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f'User with username "{username}" does not exist.')

    def _handle_create(self, *args, **options):
        """Handle the 'create' subcommand."""
        full_id = options['billing_id']
        if not is_billing_id_well_formed(full_id):
            raise CommandError(f'Billing ID {full_id} is malformed.')
        billing_activity = get_billing_activity_from_full_id(full_id)
        if isinstance(billing_activity, BillingActivity):
            raise CommandError(f'Billing ID {full_id} already exists.')
        self._validate_billing_id(
            full_id, invalid_allowed=options['ignore_invalid'])

        dry_run = options['dry_run']
        if dry_run:
            message = (
                f'Would create a BillingActivity for billing ID {full_id}.')
            self.stdout.write(self.style.WARNING(message))
        else:
            try:
                billing_activity = get_or_create_billing_activity_from_full_id(
                    full_id)
            except Exception as e:
                self.logger.exception(e)
                raise CommandError(e)
            else:
                message = (
                    f'Created BillingActivity {billing_activity.pk} for '
                    f'billing ID {full_id}.')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    def _handle_list(self, *args, **options):
        """Handle the 'list' subcommand."""
        kwargs = {'full_id': None, 'project_obj': None, 'user_obj': None}
        billing_id = options['billing_id']
        if billing_id is not None:
            kwargs['full_id'] = billing_id
        project_name = options['project_name']
        if project_name is not None:
            kwargs['project_obj'] = self._get_project_or_error(project_name)
        username = options['username']
        if username is not None:
            kwargs['user_obj'] = self._get_user_or_error(username)
        usages = get_billing_id_usages(**kwargs)

        full_id_by_billing_activity_pk = {}

        for allocation_attribute in usages.project_default:
            pk = int(allocation_attribute.value)
            if billing_id:
                full_id = billing_id
            elif pk in full_id_by_billing_activity_pk:
                full_id = full_id_by_billing_activity_pk[pk]
            else:
                full_id = BillingActivity.objects.get(pk=pk).full_id()
                full_id_by_billing_activity_pk[pk] = full_id
            project_name = allocation_attribute.allocation.project.name
            line = f'project_default,{project_name},{full_id}'
            self.stdout.write(line)

        for allocation_user_attribute in usages.recharge:
            pk = int(allocation_user_attribute.value)
            if billing_id:
                full_id = billing_id
            elif pk in full_id_by_billing_activity_pk:
                full_id = full_id_by_billing_activity_pk[pk]
            else:
                full_id = BillingActivity.objects.get(pk=pk).full_id()
                full_id_by_billing_activity_pk[pk] = full_id
            project_name = allocation_user_attribute.allocation.project.name
            username = allocation_user_attribute.allocation_user.user.username
            line = f'recharge,{project_name},{username},{full_id}'
            self.stdout.write(line)

        for user_profile in usages.user_account:
            full_id = user_profile.billing_activity.full_id()
            username = user_profile.user.username
            line = f'user_account,{username},{full_id}'
            self.stdout.write(line)

    def _handle_set(self, *args, **options):
        """Handle the 'set' subcommand."""
        billing_activity = self._get_billing_activity_or_error(
            options['billing_id'])
        self._validate_billing_id(
            billing_activity.full_id(),
            invalid_allowed=options['ignore_invalid'])

        dry_run = options['dry_run']
        set_subcommand = options['set_subcommand']
        if set_subcommand == 'project_default':
            project = self._get_project_or_error(options['project_name'])
            self._handle_set_project_default(
                project, billing_activity, dry_run=dry_run)
        elif set_subcommand == 'recharge':
            project = self._get_project_or_error(options['project_name'])
            user = self._get_user_or_error(options['username'])
            project_user = self._get_project_user_or_error(project, user)
            self._handle_set_recharge(
                project_user, billing_activity, dry_run=dry_run)
        elif set_subcommand == 'user_account':
            user = self._get_user_or_error(options['username'])
            self._handle_set_user_account(
                user, billing_activity, dry_run=dry_run)

    def _handle_set_project_default(self, project, billing_activity,
                                    dry_run=False):
        """Handle the 'project_default' subcommand of the 'set'
        subcommand."""
        entity = Entity(
            project,
            f'Project {project.name} ({project.pk})',
            ProjectBillingActivityManager)
        self._set_billing_activity_for_entity(
            entity, billing_activity, dry_run=dry_run)

    def _handle_set_recharge(self, project_user, billing_activity,
                             dry_run=False):
        """Handle the 'recharge' subcommand of the 'set' subcommand."""
        entity = Entity(
            project_user,
            (f'ProjectUser {project_user.project.name}-'
             f'{project_user.user.username} ({project_user.pk})'),
            ProjectUserBillingActivityManager)
        self._set_billing_activity_for_entity(
            entity, billing_activity, dry_run=dry_run)

    def _handle_set_user_account(self, user, billing_activity, dry_run=False):
        """Handle the 'user_account' subcommand of the 'set'
        subcommand."""
        entity = Entity(
            user,
            f'User {user.username} ({user.pk})',
            UserBillingActivityManager)
        self._set_billing_activity_for_entity(
            entity, billing_activity, dry_run=dry_run)

    def _set_billing_activity_for_entity(self, entity, billing_activity,
                                         dry_run=False):
        """Set the BillingActivity for the given Entity to the given
        one. Optionally display updates instead of performing them."""
        instance = entity.instance
        instance_str = entity.instance_str
        manager_class = entity.manager_class

        manager = manager_class(instance)

        previous = manager.billing_activity
        previous_str = (
            previous.full_id() if isinstance(previous, BillingActivity)
            else None)
        new_str = billing_activity.full_id()

        if dry_run:
            phrase = 'Would update'
            style = self.style.WARNING
        else:
            phrase = 'Updated'
            style = self.style.SUCCESS
            try:
                manager.billing_activity = billing_activity
            except Exception as e:
                self.logger.exception(e)
                raise CommandError(e)
        message = (
            f'{phrase} billing ID for {instance_str} from {previous_str} to '
            f'{new_str}.')
        self.stdout.write(style(message))
        if not dry_run:
            self.logger.info(message)

    def _validate_billing_id(self, billing_id, invalid_allowed=False):
        """Check whether the given billing ID (str) is currently valid.
        If not, raise a CommandError or write a warning to stdout based
        on whether invalidity is allowed."""
        if not is_billing_id_valid(billing_id):
            message = f'Billing ID {billing_id} is invalid.'
            if invalid_allowed:
                message += ' Proceeding anyway.'
                self.stdout.write(self.style.WARNING(message))
            else:
                raise CommandError(message)


def add_billing_id_argument(parser, is_optional=False):
    """Add an argument 'billing_id' to the given argparse parser to
    accept a billing ID. Optionally make it an option rather than a
    positional argument."""
    name = int(is_optional) * '--' + 'billing_id'
    parser.add_argument(name, help='A billing ID (e.g., 123456-789).', type=str)


def add_ignore_invalid_argument(parser):
    """Add an optional argument '--ignore_invalid' to the given argparse
    parser to indicate that an action involving a billing ID should be
    taken, even if the ID is invalid."""
    parser.add_argument(
        '--ignore_invalid',
        action='store_true',
        help='Allow the billing ID to be invalid.')


def add_project_name_argument(parser, is_optional=False):
    """Add an argument 'project_name' to the given argparse parser to
    accept the name of a Project. Optionally make it an option rather
    than a positional argument."""
    name = int(is_optional) * '--' + 'project_name'
    parser.add_argument(name, help='The name of a project.', type=str)


def add_username_argument(parser, is_optional=False):
    """Add an argument 'username' to the given argparse parser to accept
    the username of a User. Optionally make it an option rather than a
    positional argument."""
    name = int(is_optional) * '--' + 'username'
    parser.add_argument(name, help='The username of a user.', type=str)


class Entity(object):
    """A wrapper for storing details of a database object to set a
    BillingActivity for."""

    def __init__(self, instance, instance_str, manager_class):
        """Store the instance to update, a string representation of it,
        and the BillingActivity manager class to use."""
        self.instance = instance
        self.instance_str = instance_str
        self.manager_class = manager_class
