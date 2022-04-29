import logging

from tqdm import tqdm

from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Command to set a common password for users in the test database.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--password', help='Password to set for all '
                                               'users in test database.',
                            type=str, required=True)

    def handle(self, *args, **options):
        """ Set user password for all users in test database """

        if settings.DEBUG:
            password = options['password']
            for user in tqdm(User.objects.all()):
                user.set_password(password)
                user.save()

            message = f'Set "{password}" as password for ' \
                      f'{User.objects.count()} users.'
            self.stdout.write(self.style.SUCCESS(message))
        else:
            raise CommandError('Cannot set passwords if DEBUG == False.')
