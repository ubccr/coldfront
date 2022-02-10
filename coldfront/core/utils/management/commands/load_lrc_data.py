from django.core.management.base import BaseCommand
import logging


"""An admin command with subcommands that load existing LRC data from various
data sources."""


class Command(BaseCommand):

    help = 'Loads existing LRC data from provided data sources.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self.add_subparsers(subparsers)

    @staticmethod
    def add_subparsers(subparsers):
        """Add subcommands and their respective parsers."""

        def add_file_argument(parser, file_arg_name):
            """Add an argument to the given parser to accept a file
            path."""
            parser.add_argument(
                file_arg_name,
                help=f'The path to the {file_arg_name} file.',
                type=str)

        all_parser = subparsers.add_parser('all', help='Run all subcommands.')
        for name in ('passwd_file', 'group_file', 'billing_file'):
            add_file_argument(all_parser, name)

        subparsers.add_parser(
            'allocations', help='Create allocation-related objects.')

        billing_ids_parser = subparsers.add_parser(
            'billing_ids',
            help='Load IDs to be used for monthly billing from a file.')
        add_file_argument(billing_ids_parser, 'billing_file')

        subparsers.add_parser(
            'project_pis_and_managers',
            help=(
                'Load Project PIs and Managers from a pre-defined '
                'spreadsheet.'))

        projects_and_project_users_parser = subparsers.add_parser(
            'projects_and_project_users',
            help=(
                'Load Projects and their ProjectUsers from the cluster group '
                'file.'))
        add_file_argument(projects_and_project_users_parser, 'group_file')

        users_parser = subparsers.add_parser(
            'users', help='Load users from the cluster passwd file.')
        add_file_argument(users_parser, 'passwd_file')

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_all(self, *args, **options):
        """Handle the 'all' subcommand."""
        self.handle_users(options['passwd_file'])
        self.handle_projects_and_project_users(options['group_file'])
        self.handle_project_pis_and_managers()
        self.handle_allocations()
        self.handle_billing_ids(options['billing_file'])

    def handle_allocations(self, *args, **options):
        """Handle the 'allocations' subcommand."""
        pass

    def handle_billing_ids(self, *args, **options):
        """Handle the 'billing_ids' subcommand."""
        pass

    def handle_project_pis_and_managers(self, *args, **options):
        """Handle the 'project_pis_and_managers' subcommand."""
        pass

    def handle_projects_and_project_users(self, *args, **options):
        """Handle the 'projects_and_project_users' subcommand."""
        pass

    def handle_users(self, *args, **options):
        """Handle the 'users' subcommand."""
        pass
