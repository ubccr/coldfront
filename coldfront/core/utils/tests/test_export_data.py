import datetime
import json
from decimal import Decimal

import pytz
import sys
from csv import DictReader
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError

from coldfront.api.statistics.utils import get_accounting_allocation_objects, \
    create_project_allocation, create_user_project_allocation
from coldfront.config import settings
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUser, ProjectUserStatusChoice, ProjectUserRoleChoice, \
    ProjectAllocationRequestStatusChoice, SavioProjectAllocationRequest, \
    VectorProjectAllocationRequest

DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
ABR_DATE_FORMAT = '%m-%d-%Y'


class TestBaseExportData(TestBase):
    def setUp(self):
        """Setup test data"""
        super().setUp()

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        # Create a Project and ProjectUsers.
        project = Project.objects.create(
            name='project0', status=project_status)
        setattr(self, 'project0', project)
        for j in range(2):
            ProjectUser.objects.create(
                user=getattr(self, f'user{j}'), project=project,
                role=user_role, status=project_user_status)

        # Create a compute allocation for the Project.
        allocation = Decimal('1000.00')
        create_project_allocation(project, allocation)

        # Create a compute allocation for each User on the Project.
        for j in range(2):
            create_user_project_allocation(
                getattr(self, f'user{j}'), project, allocation / 2)

        self.cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        allocation_object = get_accounting_allocation_objects(self.project0)
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

        # create test jobs
        self.current_time = datetime.datetime.now(tz=datetime.timezone.utc)

        self.job1 = Job.objects.create(jobslurmid='1',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=5),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=4),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=3),
                                       userid=self.user0,
                                       partition='savio,savio2')

        self.job2 = Job.objects.create(jobslurmid='2',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=8),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=6),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=4),
                                       userid=self.user1,
                                       partition='savio_bigmem,savio2')

        self.job3 = Job.objects.create(jobslurmid='3',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=13),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=10),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=7),
                                       userid=self.user0,
                                       partition='savio3')

    def call_command(self, *args):
        """Call the command with the given arguments, returning the messages
        written to stdout and stderr."""

        out, err = StringIO(), StringIO()
        args = [*args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)

        return out.getvalue(), err.getvalue()

    def convert_output(self, out, format):
        if format == 'json':
            output = json.loads(''.join(out))
        elif format == 'csv':
            output = [line.split(',') for line in
                      out.replace('\r', '').split('\n')
                      if line != '']
        else:
            raise CommandError('convert_output out_format must be either '
                               '\"csv\" or \"json\"')

        return output


class TestLatestJobsByUser(TestBaseExportData):
    """ Test class to test export data subcommand latest_jobs_by_user runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_json_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as JSON"""

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=json')
        output = self.convert_output(output, 'json')

        self.assertEqual(len(output), 2)
        for index in range(2):
            item = output[index]
            self.assertEqual(item['username'], f'user{index}')
            self.assertEqual(item['jobslurmid'], f'{index + 1}')
            job = Job.objects.get(jobslurmid=f'{index + 1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    def test_json_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=json',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'json')

        self.assertEqual(len(output), 1)
        for index in range(1):
            item = output[index]
            self.assertEqual(item['username'], f'user{index}')
            self.assertEqual(item['jobslurmid'], f'{index + 1}')
            job = Job.objects.get(jobslurmid=f'{index + 1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    def test_csv_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as CSV"""

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=csv')
        output = self.convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item,
                                 ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')

    def test_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=csv',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item,
                                 ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')


class TestNewClusterAccounts(TestBaseExportData):
    """Test class to test export data subcommand new_cluster_accounts runs
    correctly."""

    def setUp(self):
        """Setup test data"""
        super().setUp()

        self.pre_time = utc_now_offset_aware().replace(tzinfo=None,
                                                       microsecond=0)

    def convert_time_to_utc(self, time):
        """Convert naive LA time to UTC time"""
        local_tz = pytz.timezone('America/Los_Angeles')
        tz = pytz.timezone(settings.TIME_ZONE)
        naive_dt = datetime.datetime.combine(time, datetime.datetime.min.time())
        new_time = local_tz.localize(naive_dt).astimezone(tz)
        return new_time

    def test_json_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as JSON"""
        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=json')
        output = self.convert_output(output, 'json')

        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        for index, item in enumerate(output):
            self.assertEqual(item['username'], f'user{index}')
            date_created = \
                datetime.datetime.strptime(item['date_created'],
                                           DATE_FORMAT)
            self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    def test_json_with_date(self):
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

        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=json',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'json')

        # this should only output the cluster account creation for user1
        post_time = utc_now_offset_aware().replace(tzinfo=None, microsecond=0)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['username'], 'user1')
        date_created = \
            datetime.datetime.strptime(output[0]['date_created'],
                                       DATE_FORMAT)
        self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    def test_csv_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as CSV"""
        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=csv')
        output = self.convert_output(output, 'csv')

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

    def test_csv_with_date(self):
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

        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=csv',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'csv')

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

    def test_no_dates(self):
        """Testing job_avg_queue_time with NO date args passed"""
        output, error = self.call_command('export_data',
                                          'job_avg_queue_time')

        self.assertIn('48hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_two_dates(self):
        """Testing job_avg_queue_time with BOTH date args passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--start_date={start_date}',
                                          f'--end_date={end_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_start_date(self):
        """Testing job_avg_queue_time with only start date arg passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--start_date={start_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_end_date(self):
        """Testing job_avg_queue_time with only end date arg passed"""
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--end_date={end_date}')
        self.assertIn('60hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_partition(self):
        """Testing job_avg_queue_time with parition arg passed"""
        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--partition=savio_bigmem')
        self.assertIn('48hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    def test_errors(self):
        # invalid date error
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%Y-%d-%m')
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--start_date={start_date}',
                                              f'--end_date={end_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # end date is before start date
        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--start_date={end_date}',
                                              f'--end_date={start_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # no jobs found with the passed args
        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--partition=test_partition')
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

        for index in range(10):
            project = Project.objects.create(
                name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                status=active_status)

        for index in range(10, 20):
            project = Project.objects.create(
                name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                status=inactive_status)

        total_projects = Project.objects.all()
        active_projects = total_projects.filter(status=active_status)
        fc_projects = total_projects.filter(name__istartswith='fc_')

        fc_project_ids = list(map(lambda x: x[0], fc_projects.values_list('id')))
        active_project_ids = list(map(lambda x: x[0], active_projects.values_list('id')))

        pi_table = []
        for project in total_projects:
            pis = project.pis()
            table = [f'{pi.first_name} {pi.last_name} ({pi.email})' for pi in pis]

            if table != []:
                pi_table.append(table)
            else:
                pi_table.append(None)

        manager_table = []
        for project in total_projects:
            managers = project.managers()
            table = [f'{manager.first_name} {manager.last_name} ({manager.email})'
                     for manager in managers]

            if table != []:
                manager_table.append(table)
            else:
                manager_table.append(None)

        status_table = []
        for project in total_projects:
            status_table.append(str(project.status))

        header = ['id', 'created', 'modified', 'name', 'title', 'description']
        query_set_ = total_projects.values_list(*header)

        query_set = []
        for index, project in enumerate(query_set_):
            project = list(project)
            project.extend([status_table[index],
                            ';'.join(pi_table[index] or []),
                            ';'.join(manager_table[index] or [])])
            query_set.append(project)

        # convert created and modified fields to strings
        base_queryset = []
        final_header = header + ['status', 'pis', 'manager']
        for project in query_set:
            project[1] = str(project[1])
            project[2] = str(project[2])
            base_queryset.append(dict(zip(final_header, project)))

        self.fc_queryset = [project for project in base_queryset if project['id'] in fc_project_ids]
        self.active_queryset = [
            project for project in base_queryset if project['id'] in active_project_ids]
        self.base_queryset = base_queryset

    def test_default(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.base_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    def test_active_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--active_only', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.active_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    def test_allowance_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--allowance_type=fc_', stdout=out,
                     stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.fc_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    def test_format(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=json', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.base_queryset

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)


class TestNewProjectRequests(TestBase):
    """ Test class to test export data subcommand new_project_requests runs correctly """

    def setUp(self):
        super().setUp()

        project_status = ProjectStatusChoice.objects.get(name='Inactive')
        request_status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Approved - Complete')

        savio_headers = ['id', 'created', 'modified',
                         'allocation_type', 'survey_answers', 'state', 'pool']
        vector_headers = ['id', 'created', 'modified']
        additional_headers = ['project', 'status', 'requester', 'pi']

        # create sample requests
        projects, statuses, requesters, pis = [], [], [], []
        for index in range(10):
            test_user = User.objects.create(
                first_name=f'Test{index}', last_name=f'User{index}',
                username=f'user{index}', email=f'user{index}@nonexistent.com')
            project = Project.objects.create(name=f'test_project_{index}', status=project_status)

            projects.append(project.name)
            statuses.append(request_status.name)
            requesters.append(f'{test_user.first_name} ' +
                              f'{test_user.last_name} ' +
                              f'({test_user.email})')
            pis.append(f'{test_user.first_name} ' +
                       f'{test_user.last_name} ' +
                       f'({test_user.email})')

            if index < 5:
                SavioProjectAllocationRequest.objects.create(
                    requester=test_user,
                    allocation_type=SavioProjectAllocationRequest.FCA,
                    project=project,
                    survey_answers={'abcd': 'bcda'},
                    pi=test_user,
                    status=ProjectAllocationRequestStatusChoice.objects.get(
                        name='Approved - Complete'))

            else:
                VectorProjectAllocationRequest.objects.create(
                    requester=test_user,
                    project=project,
                    pi=test_user,
                    status=ProjectAllocationRequestStatusChoice.objects.get(
                        name='Approved - Complete'))

        savio_queryset = []
        savio_requests = SavioProjectAllocationRequest.objects.all().values_list(*savio_headers)
        for project, project_status, requester, pi, request in \
                zip(projects, statuses, requesters, pis, savio_requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, project_status, requester, pi])
            savio_queryset.append(request)

        vector_queryset = []
        vector_requests = VectorProjectAllocationRequest.objects.all().values_list(*vector_headers)
        for project, project_status, requester, pi, request in \
                zip(projects[5:], statuses[5:], requesters[5:], pis[5:], vector_requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, project_status, requester, pi])
            vector_queryset.append(request)

        savio_headers.extend(additional_headers)
        vector_headers.extend(additional_headers)

        self.savio_queryset = list(map(lambda r: dict(zip(savio_headers, r)), savio_queryset))
        self.vector_queryset = list(map(lambda r: dict(zip(vector_headers, r)), vector_queryset))

    def test_savio(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=csv', '--type=savio', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.savio_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    def test_vector(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=csv', '--type=vector', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.vector_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    def test_json(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=json', '--type=savio', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.savio_queryset

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)
