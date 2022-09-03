from django.core.management.base import BaseCommand

from coldfront.core.test_helpers import utils

class Command(BaseCommand):
    help = 'automatically check pages for common issues'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('password', nargs='+', type=str)

    def handle(self, *args, **options):
        username = options['username'][0]
        password = options['password'][0]
        client = utils.login_return_client(username, password)
        utils.confirm_loads(client, "/project/?show_all_projects=on")
        utils.confirm_loads(client, "/allocation/?show_all_allocations=on")
