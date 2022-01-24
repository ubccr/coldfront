from django.core.management.base import BaseCommand

"""An admin command that exports the results of useful database queries
in user-friendly formats."""


class Command(BaseCommand):

    help = 'Exports data based on the requested query.'

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
        # TODO: Delete these samples and their handlers.
        sample_a_parser = subparsers.add_parser(
            'sample_a', help='Export sample data (a).')
        sample_a_parser.add_argument(
            '--allowance_type',
            choices=['ac_', 'co_', 'fc_', 'ic_', 'pc_'],
            help='Filter projects by the given allowance type.',
            type=str)

        sample_b_parser = subparsers.add_parser(
            'sample_b', help='Export sample data (b).')
        sample_b_parser.add_argument(
            'format',
            choices=['csv', 'json'],
            help='Export results in the given format.',
            type=str)

        # TODO: Add parsers here.

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_sample_a(self, *args, **options):
        """Handle the 'sample_a' subcommand."""
        if options['allowance_type']:
            allowance_type = options['allowance_type']
        else:
            allowance_type = ''
        message = f'Allowance Type: {allowance_type}'
        self.stdout.write(self.style.SUCCESS(message))
        # Etc.

    def handle_sample_b(self, *args, **options):
        """Handle the 'sample_b' subcommand."""
        fmt = options['format']
        message = f'Format: {fmt}'
        self.stderr.write(self.style.ERROR(message))
        # Etc.
