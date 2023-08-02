import logging
import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from coldfront.core.user.utils_.merge_users import UserMergeRunner
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.reporting.report_message_strategy import EnqueueForLoggingStrategy
from coldfront.core.utils.reporting.report_message_strategy import WriteViaCommandStrategy


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

        write_via_command_strategy = WriteViaCommandStrategy(self)
        enqueue_for_logging_strategy = EnqueueForLoggingStrategy(self.logger)
        reporting_strategies = [
            write_via_command_strategy, enqueue_for_logging_strategy]

        user_merge_runner = UserMergeRunner(
            user_1, user_2, reporting_strategies=reporting_strategies)

        src_user = user_merge_runner.src_user
        src_user_str = (
            f'{src_user.username} ({src_user.pk}, {src_user.first_name} '
            f'{src_user.last_name})')
        dst_user = user_merge_runner.dst_user
        dst_user_str = (
            f'{dst_user.username} ({dst_user.pk}, {dst_user.first_name} '
            f'{dst_user.last_name})')

        self.stdout.write(self.style.WARNING(f'Source: {src_user_str}'))
        self.stdout.write(self.style.WARNING(f'Destination: {dst_user_str}'))

        if dry_run:
            user_merge_runner.dry_run()
            self.stdout.write(self.style.WARNING('Dry run of merge complete.'))
        else:
            enqueue_for_logging_strategy.warning(
                f'Initiating a merge of source User {src_user_str} into '
                f'destination User {dst_user_str}.')
            try:
                user_merge_runner.run()
            except Exception as e:
                # TODO
                pass
            else:
                self.stdout.write(self.style.SUCCESS('Merge complete.'))
                enqueue_for_logging_strategy.success(
                    f'Successfully merged source User {src_user_str} into '
                    f'destination User {dst_user_str}.')
                enqueue_for_logging_strategy.log_queued_messages()
