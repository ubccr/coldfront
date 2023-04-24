from django.core.management.base import BaseCommand

from coldfront.plugins.fasrc_monitoring.utils import run_view_db_checks

class Command(BaseCommand):
    help = 'automatically check pages and database entries for common issues.'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('password', nargs='+', type=str)

    def handle(self, *args, **options):
        username = options['username'][0]
        password = options['password'][0]
        run_view_db_checks(username, password)
