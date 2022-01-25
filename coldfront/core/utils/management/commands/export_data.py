import csv
import json
from csv import DictWriter
import datetime
from sys import stdout, stderr

import pytz
from django.core import serializers

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Value, F, CharField, DateTimeField, Func
from django.db.models.functions import Cast, TruncSecond

from coldfront.config import settings
from coldfront.core.statistics.models import Job

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

        user_list_parser = subparsers.add_parser('user_list',
                                                 help='Export list of users'
                                                      'who have submitted a job'
                                                      'since a given date')
        user_list_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        user_list_parser.add_argument(
            '--date',
            help='Date that users last submitted a job. '
                 'Must take the form of MM-DD-YYYY',
            type=valid_date)

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

    def handle_user_list(self, *args, **options):
        """Handle the 'user_list' subcommand."""
        date = options.get('date', None)
        format = options.get('format', None)

        query_set = Job.objects.all().annotate(str_submitdate=Func(
            F('submitdate'),
            Value('MM-dd-yyyy hh:mm:ss'),
            function='to_char',
            output_field=CharField()
        ))

        if date:
            date = self.convert_time_to_utc(date)
            query_set = query_set.filter(submitdate__gte=date)

        query_set = query_set.order_by('userid', '-submitdate').\
            distinct('userid')

        if format == 'csv':
            query_set = query_set.values_list('userid__username', 'jobslurmid', 'str_submitdate')
            header = ['user__username', 'last_job_id', 'last_job_submitdate']
            self.to_csv(query_set,
                        header=header,
                        output=options.get('stdout', stdout),
                        error=options.get('stderr', stderr))

        else:
            query_set = query_set.values('userid__username', 'jobslurmid', 'str_submitdate')
            self.to_json(query_set,
                         output=options.get('stdout', stdout),
                         error=options.get('stderr', stderr))

    @staticmethod
    def to_csv(query_set, header=None, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        header: csv header to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet')
            return

        try:
            writer = csv.writer(output)

            if header:
                writer.writerow(header)

            for x in query_set:
                writer.writerow(x)

        except Exception as e:
            error.write(str(e))

    @staticmethod
    def to_json(query_set, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet')
            return

        try:
            json_output = json.dumps(list(query_set))
            output.writelines(json_output)
        except Exception as e:
            error.write(str(e))

    @staticmethod
    def convert_time_to_utc(time):
        """Convert naive LA time to UTC time"""
        local_tz = pytz.timezone('America/Los_Angeles')
        tz = pytz.timezone(settings.TIME_ZONE)
        naive_dt = datetime.datetime.combine(time, datetime.datetime.min.time())
        new_time = local_tz.localize(naive_dt).astimezone(tz).isoformat()

        return new_time


def valid_date(s):
    try:
        return datetime.datetime.strptime(s, '%m-%d-%Y')
    except ValueError:
        msg = f'{s} is not a valid date. ' \
              f'Must take the form of "MM-DD-YYYY".'
        raise CommandError(msg)