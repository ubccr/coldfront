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
                                       submitdate=self.current_time - datetime.timedelta(days=7),
                                       startdate=self.current_time - datetime.timedelta(days=6),
                                       enddate=self.current_time - datetime.timedelta(days=5),
                                       userid=self.user2)

        self.job3 = Job.objects.create(jobslurmid='3',
                                       submitdate=self.current_time - datetime.timedelta(days=12),
                                       startdate=self.current_time - datetime.timedelta(days=10),
                                       enddate=self.current_time - datetime.timedelta(days=9),
                                       userid=self.user1)


class TestUserList(TestBaseExportData):
    """ Test class to test export data subcommand user_list runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_user_list_json_no_date(self):
        """Testing user_list subcommand with NO date arg passed,
        exporting as JSON"""

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=json',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))

        self.assertEqual(len(output), 2)
        for index in range(2):
            item = output[index]
            self.assertEqual(item['username'], f'user{index+1}')
            self.assertEqual(item['jobslurmid'], f'{index+1}')
            job = Job.objects.get(jobslurmid=f'{index+1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         '%m-%d-%Y %H:%M:%S')
            self.assertEqual(item['submit_date'], submit_date_str)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_user_list_json_with_date(self):
        """Testing user_list subcommand with date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%m-%d-%Y')

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=json',
                     f'--start_date={start_date}', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))

        self.assertEqual(len(output), 1)
        for index in range(1):
            item = output[index]
            self.assertEqual(item['username'], f'user{index+1}')
            self.assertEqual(item['jobslurmid'], f'{index+1}')
            job = Job.objects.get(jobslurmid=f'{index+1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         '%m-%d-%Y %H:%M:%S')
            self.assertEqual(item['submit_date'], submit_date_str)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_user_list_csv_no_date(self):
        """Testing user_list subcommand with NO date arg passed,
        exporting as CSV"""

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=csv',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = csv.reader(out.readlines())

        for index, item in enumerate(reader):
            if index == 0:
                self.assertEqual(item, ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         '%m-%d-%Y %H:%M:%S')
                self.assertEqual(item[2], submit_date_str)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_user_list_csv_with_date(self):
        """Testing user_list subcommand with date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%m-%d-%Y')

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=csv',
                     f'--start_date={start_date}', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = csv.reader(out.readlines())

        for index, item in enumerate(reader):
            if index == 0:
                self.assertEqual(item, ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             '%m-%d-%Y %H:%M:%S')
                self.assertEqual(item[2], submit_date_str)

        err.seek(0)
        self.assertEqual(err.read(), '')


class TestNewUserAccount(TestAllocationBase):
    """Test class to test export data subcommand new_user_account runs
    correctly."""

    def setUp(self):
        """Setup test data"""
        self.pre_time = utc_now_offset_aware().replace(tzinfo=None)

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

    def test_new_user_account_json_no_date(self):
        """Testing new_user_account subcommand with NO date arg passed,
        exporting as JSON"""
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_user_account', '--format=json',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))

        post_time = utc_now_offset_aware().replace(tzinfo=None)
        for index, item in enumerate(output):
            self.assertEqual(item['username'], f'user{index}')
            date_created = \
                datetime.datetime.strptime(item['date_created'],
                                           '%m-%d-%Y %H:%M:%S')
            self.assertTrue(self.pre_time <= date_created <= post_time)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_new_user_account_json_with_date(self):
        """Testing new_user_account subcommand with ONE date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), '%m-%d-%Y')

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

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_user_account', '--format=json',
                     f'--start_date={start_date}', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))

        # this should only output the cluster account creation for user1
        post_time = utc_now_offset_aware().replace(tzinfo=None)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['username'], 'user1')
        date_created = \
            datetime.datetime.strptime(output[0]['date_created'],
                                       '%m-%d-%Y %H:%M:%S')
        self.assertTrue(self.pre_time <= date_created <= post_time)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_new_user_account_csv_no_date(self):
        """Testing new_user_account subcommand with NO date arg passed,
        exporting as CSV"""

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_user_account', '--format=csv',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = csv.reader(out.readlines())

        post_time = utc_now_offset_aware().replace(tzinfo=None)
        for index, item in enumerate(reader):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               '%m-%d-%Y %H:%M:%S')
                self.assertTrue(self.pre_time <= date_created <= post_time)

            err.seek(0)
            self.assertEqual(err.read(), '')

    def test_new_user_account_csv_with_date(self):
        """Testing new_user_account subcommand with ONE date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), '%m-%d-%Y')

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

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_user_account', '--format=csv',
                     f'--start_date={start_date}', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = csv.reader(out.readlines())

        post_time = utc_now_offset_aware().replace(tzinfo=None)
        for index, item in enumerate(reader):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], 'user1')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               '%m-%d-%Y %H:%M:%S')
                self.assertTrue(self.pre_time <= date_created <= post_time)

        err.seek(0)
        self.assertEqual(err.read(), '')


class TestJobAvgQueueTime(TestBaseExportData):
    """ Test class to test export data subcommand job_avg_queue_time
    runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_job_avg_queue_time_no_dates(self):
        """Testing job_avg_queue_time with NO date args passed"""
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'job_avg_queue_time', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        self.assertIn('32hrs 0mins 0secs', out.read())

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_job_avg_queue_time_with_dates(self):
        """Testing job_avg_queue_time with BOTH date args passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%m-%d-%Y')
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), '%m-%d-%Y')

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'job_avg_queue_time',
                     f'--start_date={start_date}', f'--end_date={end_date}',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        self.assertIn('24hrs 0mins 0secs', out.read())

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_job_avg_queue_time_errors(self):
        # invalid date error
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%Y-%d-%m')
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), '%m-%d-%Y')

        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('export_data', 'job_avg_queue_time',
                         f'--start_date={start_date}', f'--end_date={end_date}',
                         stdout=out, stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')

            err.seek(0)
            self.assertEqual(err.read(), '')

        # only one date
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('export_data', 'job_avg_queue_time',
                         f'--start_date={start_date}',
                         stdout=out, stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')

            err.seek(0)
            self.assertEqual(err.read(), '')

        # end date is before start date
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('export_data', 'job_avg_queue_time',
                         f'--start_date={end_date}', f'--end_date={start_date}',
                         stdout=out, stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')

            err.seek(0)
            self.assertEqual(err.read(), '')


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
