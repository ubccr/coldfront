from django.core.management.base import BaseCommand

from coldfront.plugins.fasrc_monitoring.utils import run_view_db_checks
from coldfront.core.utils.common import import_from_settings
from coldfront.config.env import ENV

class Command(BaseCommand):
    help = 'automatically check pages and database entries for common issues.'

    def handle(self, *args, **options):
        username = ENV.str('TESTUSER')
        password = ENV.str('TESTPASS')
        run_view_db_checks(username, password)
