import csv
import json
import datetime
from sys import stdout, stderr

import pytz

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Value, F, CharField, Func, \
    DurationField, ExpressionWrapper

from coldfront.config import settings
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.statistics.models import Job
from coldfront.core.project.models import Project

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
        user_list_parser = \
            subparsers.add_parser('user_list',
                                  help='Export list of users who have '
                                       'submitted a job since a given date.')
        user_list_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        user_list_parser.add_argument(
            '--start_date',
            help='Date that users last submitted a job. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        new_user_account_parser = \
            subparsers.add_parser('new_user_account',
                                  help='Export list of new user accounts '
                                       'created since a given date.')
        new_user_account_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        new_user_account_parser.add_argument(
            '--start_date',
            help='Date that users last created an account. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        job_avg_queue_time_parser = \
            subparsers.add_parser('job_avg_queue_time',
                                  help='Export average queue time for jobs'
                                       'between the given dates.')
        job_avg_queue_time_parser.add_argument(
            '--start_date',
            help='Starting date for jobs. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)
        job_avg_queue_time_parser.add_argument(
            '--end_date',
            help='Ending date for jobs. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)
        job_avg_queue_time_parser.add_argument(
            '--allowance_type',
            choices=['ac_', 'co_', 'fc_', 'ic_', 'pc_'],
            help='Filter projects by the given allowance type.',
            type=str)

        project_subparser = subparsers.add_parser('projects',
                                                  help='Export projects data')
        project_subparser.add_argument('--allowance_type',
                                       choices=['ac_', 'co_',
                                                'fc_', 'ic_', 'pc_'],
                                       help='Filter projects by the given allowance type.',
                                       type=str)
        project_subparser.add_argument('--format',
                                       choices=['csv', 'json'],
                                       required=True,
                                       help='Export results in the given format.',
                                       type=str)
        project_subparser.add_argument('--active_only',
                                       action='store_true')

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_user_list(self, *args, **options):
        """Handle the 'user_list' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)

        query_set = Job.objects.annotate(
            submit_date=Func(
                F('submitdate'),
                Value('MM-dd-yyyy HH24:mi:ss'),
                function='to_char',
                output_field=CharField()
            ),
            username=F('userid__username')
        )

        if date:
            date = self.convert_time_to_utc(date)
            query_set = query_set.filter(submitdate__gte=date)

        query_set = query_set.order_by('userid', '-submitdate').\
            distinct('userid')

        if format == 'csv':
            query_set = query_set.values_list('username', 'jobslurmid', 'submit_date')
            header = ['username', 'jobslurmid', 'submit_date']
            self.to_csv(query_set,
                        header=header,
                        output=options.get('stdout', stdout),
                        error=options.get('stderr', stderr))

        else:
            query_set = query_set.values('username', 'jobslurmid', 'submit_date')
            self.to_json(query_set,
                         output=options.get('stdout', stdout),
                         error=options.get('stderr', stderr))

    def handle_new_user_account(self, *args, **options):
        """Handle the 'new_user_account' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        query_set = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=cluster_account_status,
            value='Active')

        query_set = query_set.annotate(
            date_created=Func(
                F('created'),
                Value('MM-dd-yyyy HH24:mi:ss'),
                function='to_char',
                output_field=CharField()
            ),
            username=F('allocation_user__user__username')
        )

        if date:
            date = self.convert_time_to_utc(date)
            query_set = query_set.filter(created__gte=date)

        query_set = query_set.order_by('username', '-created'). \
            distinct('username')

        if format == 'csv':
            query_set = query_set.values_list('username', 'date_created')
            header = ['username', 'date_created']
            self.to_csv(query_set,
                        header=header,
                        output=options.get('stdout', stdout),
                        error=options.get('stderr', stderr))

        else:
            query_set = query_set.values('username', 'date_created')
            self.to_json(query_set,
                         output=options.get('stdout', stdout),
                         error=options.get('stderr', stderr))

    def handle_job_avg_queue_time(self, *args, **options):
        """Handle the 'job_avg_queue_time' subcommand."""
        start_date = options.get('start_date', None)
        end_date = options.get('end_date', None)
        allowance_type = options.get('allowance_type', None)

        if bool(start_date) ^ bool(end_date):
            message = 'Must either input NO dates or BOTH ' \
                      'start_date and end_date'
            raise CommandError(message)

        elif end_date and start_date and end_date < start_date:
            message = 'start_date must be before end_date.'
            raise CommandError(message)

        query_set = Job.objects.annotate(queue_time=ExpressionWrapper(
            F('startdate') - F('submitdate'), output_field=DurationField()))

        if start_date and end_date:
            start_date = self.convert_time_to_utc(start_date)
            end_date = self.convert_time_to_utc(end_date)

            query_set = query_set.filter(submitdate__gte=start_date,
                                         submitdate__lte=end_date)

        if allowance_type:
            query_set = query_set.filter(accountid__name__startswith=allowance_type)

        query_set = query_set.values_list('queue_time', flat=True)
        avg_queue_time = sum(query_set, datetime.timedelta()) / query_set.count()

        total_seconds = int(avg_queue_time.total_seconds())
        hours, remainder = divmod(total_seconds, 60*60)
        minutes, seconds = divmod(remainder, 60)
        time_str = '{}hrs {}mins {}secs'.format(hours, minutes, seconds)

        self.stdout.write(self.style.SUCCESS(time_str))

    def handle_projects(self, *args, **kwargs):
        format = kwargs['format']
        active_only = kwargs['active_only']
        allowance_type = kwargs['allowance_type']
        projects = Project.objects.all()

        if allowance_type:
            projects = projects.filter(name__istartswith=allowance_type)

        if active_only:
            projects = projects.filter(status__name__istartswith='Active')

        if format == 'csv':
            header = dict(projects[0].__dict__)
            header.pop('_state')
            query_set = projects.values_list(*header)

            self.to_csv(query_set,
                        header=header,
                        output=kwargs.get('stdout', stdout),
                        error=kwargs.get('stderr', stderr))

        elif format == 'json':
            query_set = [dict(project.__dict__) for project in projects]
            for query in query_set:
                query.pop("_state")

            self.to_json(query_set,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))

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
            json_output = json.dumps(list(query_set), indent=4, default=str)
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