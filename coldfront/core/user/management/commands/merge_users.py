import logging
import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from coldfront.core.user.utils_.user_merge_utils import UserMergeRunner
from coldfront.core.utils.common import add_argparse_dry_run_argument


"""An admin command that merges two Users into one."""


class Command(BaseCommand):

    help = (
        'Merge two Users into one. The command chooses one instance, transfers '
        'that instance\'s relationships, requests, etc. to the other, and then '
        'deletes it.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)
        parser.add_argument(
            'username_1', help='The username of the first user.', type=str)
        parser.add_argument(
            'username_2', help='The username of the second user.', type=str)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if not dry_run:
            user_confirmation = input(
                'Are you sure you wish to proceed? [Y/y/N/n]: ')
            if user_confirmation.strip().lower() != 'y':
                self.stdout.write(self.style.WARNING('Merge aborted.'))
                sys.exit(0)

        username_1 = options['username_1']
        try:
            user_1 = User.objects.get(username=username_1)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f'User "{username_1}" does not exist.'))
            return

        username_2 = options['username_2']
        try:
            user_2 = User.objects.get(username=username_2)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f'User "{username_2}" does not exist.'))
            return

        # TODO: Check that the first and last names of the two users match.

        user_merge_runner = UserMergeRunner(user_1, user_2)

        print(f'Src: {user_merge_runner.src_user}')
        print(f'Dst: {user_merge_runner.dst_user}')

        user_merge_runner.run()
