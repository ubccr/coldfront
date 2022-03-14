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
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    SavioProjectAllocationRequest, VectorProjectAllocationRequest


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
        latest_jobs_by_user_parser = \
            subparsers.add_parser('latest_jobs_by_user',
                                  help='Export list of users and their latest '
                                       'job if they have submitted a job since '
                                       'a given date.')
        latest_jobs_by_user_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        latest_jobs_by_user_parser.add_argument(
            '--start_date',
            help='Date since users last submitted a job. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        new_cluster_accounts_parser = \
            subparsers.add_parser('new_cluster_accounts',
                                  help='Export list of new user accounts '
                                       'created since a given date.')
        new_cluster_accounts_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        new_cluster_accounts_parser.add_argument(
            '--start_date',
            help='Date that users last created an account. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        job_avg_queue_time_parser = \
            subparsers.add_parser('job_avg_queue_time',
                                  help='Export average queue time for jobs '
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
        job_avg_queue_time_parser.add_argument(
            '--partition',
            help='Filter jobs by the partition they requested.',
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
        project_subparser.add_argument('--active_only', action='store_true')

        new_project_requests_subparser = subparsers.\
            add_parser('new_project_requests', help='Export new project requests')
        new_project_requests_subparser.add_argument('--type',
                                                    choices=['vector', 'savio'],
                                                    required=True,
                                                    help='Filter based on allocation type',
                                                    type=str)
        new_project_requests_subparser.add_argument('--format',
                                                    choices=['csv', 'json'],
                                                    required=True,
                                                    help='Export results in the given format.',
                                                    type=str)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_latest_jobs_by_user(self, *args, **options):
        """Handle the 'latest_jobs_by_user' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)
        output = options.get('stdout', stdout)
        error = options.get('stderr', stderr)
        fields = ['username', 'jobslurmid', 'submit_date']

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
            query_set = query_set.values_list(*fields)
            self.to_csv(query_set,
                        header=[*fields],
                        output=output,
                        error=error)

        else:
            query_set = query_set.values(*fields)
            self.to_json(query_set,
                         output=output,
                         error=error)

    def handle_new_cluster_accounts(self, *args, **options):
        """Handle the 'new_cluster_accounts' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)
        output = options.get('stdout', stdout)
        error = options.get('stderr', stderr)
        fields = ['username', 'date_created']

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
            query_set = query_set.values_list(*fields)
            self.to_csv(query_set,
                        header=[*fields],
                        output=output,
                        error=error)

        else:
            query_set = query_set.values(*fields)
            self.to_json(query_set,
                         output=output,
                         error=error)

    def handle_job_avg_queue_time(self, *args, **options):
        """Handle the 'job_avg_queue_time' subcommand."""
        start_date = options.get('start_date', None)
        end_date = options.get('end_date', None)
        allowance_type = options.get('allowance_type', None)
        partition = options.get('partition', None)

        if start_date and end_date and end_date < start_date:
            message = 'start_date must be before end_date.'
            raise CommandError(message)

        # only select jobs that have valid start and submit dates
        query_set = Job.objects.exclude(startdate=None, submitdate=None)

        query_set = query_set.annotate(queue_time=ExpressionWrapper(
            F('startdate') - F('submitdate'), output_field=DurationField()))

        if start_date:
            start_date = self.convert_time_to_utc(start_date)
            query_set = query_set.filter(submitdate__gte=start_date)

        if end_date:
            end_date = self.convert_time_to_utc(end_date)
            query_set = query_set.filter(submitdate__lte=end_date)

        if allowance_type:
            query_set = query_set.filter(accountid__name__startswith=allowance_type)

        if partition:
            message = 'Filtering on job partitions may take over a minute...'
            self.stdout.write(self.style.WARNING(message))

            # further reduce query_set size before splitting partition
            query_set = query_set.filter(partition__icontains=partition)
            ids = set()

            for job in query_set.iterator():
                if partition in job.partition.split(','):
                    ids.add(job.jobslurmid)
            query_set = query_set.filter(jobslurmid__in=ids)

        if query_set.count() == 0:
            message = 'No jobs found that satisfy the passed arguments'
            raise CommandError(message)

        message = 'Calculating average job queue time...'
        self.stdout.write(self.style.WARNING(message))
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
            active_status = ProjectStatusChoice.objects.get(name='Active')
            projects = projects.filter(status=active_status)

        pi_table = []
        for project in projects:
            pis = project.pis()
            table = [f'{pi.first_name} {pi.last_name} ({pi.email})' for pi in pis]

            if table != []:
                pi_table.append(table)
            else:
                pi_table.append(None)

        manager_table = []
        for project in projects:
            managers = project.managers()
            table = [f'{manager.first_name} {manager.last_name} ({manager.email})'
                     for manager in managers]

            if table != []:
                manager_table.append(table)
            else:
                manager_table.append(None)

        status_table = []
        for project in projects:
            status_table.append(str(project.status))

        header = ['id', 'created', 'modified', 'name', 'title', 'description']
        query_set_ = projects.values_list(*header)

        query_set = []
        for index, project in enumerate(query_set_):
            project = list(project)
            project.extend([status_table[index],
                            ';'.join(pi_table[index] or []),
                            ';'.join(manager_table[index] or [])])

            query_set.append(project)

        header.extend(['status', 'pis', 'manager'])
        if format == 'csv':
            self.to_csv(query_set,
                        header=header,
                        output=kwargs.get('stdout', stdout),
                        error=kwargs.get('stderr', stderr))

        elif format == 'json':
            query_set_ = query_set
            query_set = []

            for project in query_set_:
                project = dict(zip(header, project))
                query_set.append(project)

            self.to_json(query_set,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))

    def handle_new_project_requests(self, *args, **kwargs):
        format = kwargs['format']
        type = kwargs['type']

        requests = None
        if type == 'savio':
            requests = SavioProjectAllocationRequest.objects.all()
            header = ['id', 'created', 'modified', 'allocation_type',
                      'survey_answers', 'state', 'pool']

        else:
            requests = VectorProjectAllocationRequest.objects.all()
            header = ['id', 'created', 'modified']

        additiona_headers = ['project', 'status', 'requester', 'pi']
        projects = [project.project.name for project in requests]
        statuses = [request.status.name for request in requests]

        requesters = []
        for request in requests:
            requesters.append(f'{request.requester.first_name} ' +
                              f'{request.requester.last_name} ' +
                              f'({request.requester.email})')

        pis = []
        for request in requests:
            pis.append(f'{request.pi.first_name} ' +
                       f'{request.pi.last_name} ' +
                       f'({request.pi.email})')

        query_set = []
        requests = requests.values_list(*header)
        for project, status, requester, pi, request in \
                zip(projects, statuses, requesters, pis, requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, status, requester, pi])
            query_set.append(request)

        headers = header + additiona_headers
        query_set = list(map(lambda query: dict(zip(headers, query)), query_set))

        if format == 'csv':
            query_set_ = [query.values() for query in query_set]

            self.to_csv(query_set_,
                        header=headers,
                        output=kwargs.get('stdout', stdout),
                        error=kwargs.get('stderr', stderr))

        elif format == 'json':
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
