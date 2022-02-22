import csv
import datetime
import json
import pytz
import sys
from csv import DictReader
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.config import settings
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.models import Project, ProjectStatusChoice


DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
ABR_DATE_FORMAT = '%m-%d-%Y'


def call_deactivate_command(*args):
    """Call the command with the given arguments, returning the messages
    written to stdout and stderr."""

    out, err = StringIO(), StringIO()
    args = [*args]
    kwargs = {'stdout': out, 'stderr': err}
    call_command(*args, **kwargs)

    return out.getvalue(), err.getvalue()


def convert_output(out, format):
    if format == 'json':
        output = json.loads(''.join(out))
    elif format == 'csv':
        output = [line.split(',') for line in
                  out.replace('\r', '').split('\n')
                  if line != '']
    else:
        raise CommandError('call_deactivate_command out_format must be either '
                           '\"csv\" or \"json\"')

    return output


class TestBaseExportData(TestBase):
    def setUp(self):
        """Setup test data"""
        super().setUp()

        # Create a normal users
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='Normal',
            last_name='User2',
            username='user2')

        self.password = 'password'

        for user in User.objects.all():
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

            user.set_password(self.password)
            user.save()

        # create test jobs
        self.current_time = datetime.datetime.now(tz=datetime.timezone.utc)

        self.job1 = Job.objects.create(jobslurmid='1',
                                       submitdate=self.current_time - datetime.timedelta(days=5),
                                       startdate=self.current_time - datetime.timedelta(days=4),
                                       enddate=self.current_time - datetime.timedelta(days=3),
                                       userid=self.user1)

        self.job2 = Job.objects.create(jobslurmid='2',
                                       submitdate=self.current_time - datetime.timedelta(days=8),
                                       startdate=self.current_time - datetime.timedelta(days=6),
                                       enddate=self.current_time - datetime.timedelta(days=4),
                                       userid=self.user2)

        self.job3 = Job.objects.create(jobslurmid='3',
                                       submitdate=self.current_time - datetime.timedelta(days=13),
                                       startdate=self.current_time - datetime.timedelta(days=10),
                                       enddate=self.current_time - datetime.timedelta(days=7),
                                       userid=self.user1)


class TestLatestJobsByUser(TestBaseExportData):
    """ Test class to test export data subcommand latest_jobs_by_user runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_latest_jobs_by_user_json_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as JSON"""

        output, error = call_deactivate_command('export_data',
                                                'latest_jobs_by_user',
                                                '--format=json')
        output = convert_output(output, 'json')

        self.assertEqual(len(output), 2)
        for index in range(2):
            item = output[index]
            self.assertEqual(item['username'], f'user{index+1}')
            self.assertEqual(item['jobslurmid'], f'{index+1}')
            job = Job.objects.get(jobslurmid=f'{index+1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    def test_latest_jobs_by_user_json_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = call_deactivate_command('export_data',
                                                'latest_jobs_by_user',
                                                '--format=json',
                                                f'--start_date={start_date}')
        output = convert_output(output, 'json')

        self.assertEqual(len(output), 1)
        for index in range(1):
            item = output[index]
            self.assertEqual(item['username'], f'user{index+1}')
            self.assertEqual(item['jobslurmid'], f'{index+1}')
            job = Job.objects.get(jobslurmid=f'{index+1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    def test_latest_jobs_by_user_csv_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as CSV"""

        output, error = call_deactivate_command('export_data',
                                                'latest_jobs_by_user',
                                                '--format=csv')
        output = convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')

    def test_latest_jobs_by_user_csv_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = call_deactivate_command('export_data',
                                                'latest_jobs_by_user',
                                                '--format=csv',
                                                f'--start_date={start_date}')
        output = convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')


class TestNewClusterAccounts(TestAllocationBase):
    """Test class to test export data subcommand new_cluster_accounts runs
    correctly."""

    def setUp(self):
        """Setup test data"""
        self.pre_time = utc_now_offset_aware().replace(tzinfo=None,
                                                       microsecond=0)

        super().setUp()

        self.cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        project = Project.objects.get(name='project0')
        allocation_object = get_accounting_allocation_objects(project)
        for j, project_user in enumerate(project.projectuser_set.all()):
            if project_user.role.name != 'User':
                continue

            allocation_user_objects = get_accounting_allocation_objects(
                project, user=project_user.user)

            AllocationUserAttribute.objects.create(
                allocation_attribute_type=self.cluster_account_status,
                allocation=allocation_object.allocation,
                allocation_user=allocation_user_objects.allocation_user,
                value='Active')

    def convert_time_to_utc(self, time):
        """Convert naive LA time to UTC time"""
        local_tz = pytz.timezone('America/Los_Angeles')
        tz = pytz.timezone(settings.TIME_ZONE)
        naive_dt = datetime.datetime.combine(time, datetime.datetime.min.time())
        new_time = local_tz.localize(naive_dt).astimezone(tz)
        return new_time

    def test_new_cluster_accounts_json_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as JSON"""
        output, error = call_deactivate_command('export_data',
                                                'new_cluster_accounts',
                                                '--format=json')
        output = convert_output(output, 'json')

        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        for index, item in enumerate(output):
            self.assertEqual(item['username'], f'user{index}')
            date_created = \
                datetime.datetime.strptime(item['date_created'],
                                           DATE_FORMAT)
            self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    def test_new_cluster_accounts_json_with_date(self):
        """Testing new_cluster_accounts subcommand with ONE date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        new_date = self.convert_time_to_utc(self.pre_time -
                                            datetime.timedelta(days=10))

        allocation_user_attr_obj = AllocationUserAttribute.objects.get(
            allocation_attribute_type=self.cluster_account_status,
            allocation__project__name='project0',
            allocation_user__user__username='user0',
            value='Active')

        allocation_user_attr_obj.created = new_date
        allocation_user_attr_obj.save()
        self.assertEqual(allocation_user_attr_obj.created, new_date)

        output, error = call_deactivate_command('export_data',
                                                'new_cluster_accounts',
                                                '--format=json',
                                                f'--start_date={start_date}')
        output = convert_output(output, 'json')

        # this should only output the cluster account creation for user1
        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['username'], 'user1')
        date_created = \
            datetime.datetime.strptime(output[0]['date_created'],
                                       DATE_FORMAT)
        self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    def test_new_cluster_accounts_csv_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as CSV"""
        output, error = call_deactivate_command('export_data',
                                                'new_cluster_accounts',
                                                '--format=csv')
        output = convert_output(output, 'csv')

        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               DATE_FORMAT)
                self.assertTrue(self.pre_time <= date_created <= post_time)

            self.assertEqual(error, '')

    def test_new_cluster_accounts_csv_with_date(self):
        """Testing new_cluster_accounts subcommand with ONE date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        new_date = self.convert_time_to_utc(self.pre_time -
                                            datetime.timedelta(days=10))

        allocation_user_attr_obj = AllocationUserAttribute.objects.get(
            allocation_attribute_type=self.cluster_account_status,
            allocation__project__name='project0',
            allocation_user__user__username='user0',
            value='Active')

        allocation_user_attr_obj.created = new_date
        allocation_user_attr_obj.save()
        self.assertEqual(allocation_user_attr_obj.created, new_date)

        output, error = call_deactivate_command('export_data',
                                                'new_cluster_accounts',
                                                '--format=csv',
                                                f'--start_date={start_date}')
        output = convert_output(output, 'csv')

        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], 'user1')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               DATE_FORMAT)
                self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')


class TestJobAvgQueueTime(TestBaseExportData):
    """ Test class to test export data subcommand job_avg_queue_time
    runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_job_avg_queue_time_no_dates(self):
        """Testing job_avg_queue_time with NO date args passed"""
        output, error = call_deactivate_command('export_data',
                                                'job_avg_queue_time')

        self.assertIn('48hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_job_avg_queue_time_with_two_dates(self):
        """Testing job_avg_queue_time with BOTH date args passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        output, error = call_deactivate_command('export_data',
                                                'job_avg_queue_time',
                                                f'--start_date={start_date}',
                                                f'--end_date={end_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_job_avg_queue_time_with_start_date(self):
        """Testing job_avg_queue_time with only start date arg passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = call_deactivate_command('export_data',
                                                'job_avg_queue_time',
                                                f'--start_date={start_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_job_avg_queue_time_with_end_date(self):
        """Testing job_avg_queue_time with only end date arg passed"""
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = call_deactivate_command('export_data',
                                                'job_avg_queue_time',
                                                f'--end_date={end_date}')
        self.assertIn('60hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_job_avg_queue_time_errors(self):
        # invalid date error
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%Y-%d-%m')
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        with self.assertRaises(CommandError):
            output, error = call_deactivate_command('export_data',
                                                    'job_avg_queue_time',
                                                    f'--start_date={start_date}',
                                                    f'--end_date={end_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # end date is before start date
        with self.assertRaises(CommandError):
            output, error = call_deactivate_command('export_data',
                                                    'job_avg_queue_time',
                                                    f'--start_date={end_date}',
                                                    f'--end_date={start_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')


class TestProjects(TestBase):
    """ Test class to test export data subcommand projects runs correctly """

    def setUp(self):
        super().setUp()

        # create sample projects
        active_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        prefixes = ['fc', 'ac', 'co']

        active_projects, inactive_projects = [], []
        for index in range(10):
            project = Project.objects.create(name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                                             status=active_status)
            active_projects.append(project)

        for index in range(10, 20):
            project = Project.objects.create(name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                                             status=inactive_status)
            inactive_projects.append(project)

        self.active_projects = active_projects
        self.inactive_projects = inactive_projects

        self.total_projects = []
        self.total_projects.extend(active_projects)
        self.total_projects.extend(inactive_projects)

        self.fc_projects = list(filter(
            lambda x: x.name.startswith('fc_'), self.total_projects))

    def test_projects_default(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.total_projects

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = dict(query_set[index].__dict__)
            compare.pop('_state')

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    def test_projects_active_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--active_only', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.active_projects

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = dict(query_set[index].__dict__)
            compare.pop('_state')

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    def test_projects_allowance_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--allowance_type=fc_', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.fc_projects

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = dict(query_set[index].__dict__)
            compare.pop('_state')

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    def test_projects_format(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=json',  stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.total_projects

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = dict(query_set[index].__dict__)
            compare.pop('_state')

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)
