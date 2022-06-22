from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import pytz

from coldfront.api.statistics.tests.test_job_base import TestJobBase
from coldfront.api.statistics.utils import convert_utc_datetime_to_unix_timestamp
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import ExpiringToken
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_datetime_to_display_time_zone_date

from django.contrib.auth.models import User
from django.db.models import Sum

from rest_framework.test import APIClient
from unittest.mock import patch


class TestJobList(TestJobBase):
    """A suite for testing requests to retrieve Jobs."""

    @classmethod
    def jobs_put_url(cls, jobslurmid):
        """Return the URL for making a PUT request to the Job identified
        by the given jobslurmid."""
        return f'/api/jobs/{jobslurmid}/'

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Delete the existing User and Project created by the superclass.
        self.user.delete()
        self.project.delete()

        # Create Users.
        self.num_users = 4
        for i in range(self.num_users):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = str(i + 1)
            user_profile.save()

        # Create Projects.
        self.num_projects = 2
        project_status = ProjectStatusChoice.objects.get(name='Active')
        allocation_pks = dict()

        # Create compute allocations for the Projects.
        allocation_amount = Decimal('1000.00')
        for i in range(self.num_projects):
            project = Project.objects.create(
                name=f'PROJECT_{i}', status=project_status)
            allocation_objects = create_project_allocation(
                project, allocation_amount)
            allocation_objects.allocation.start_date = \
                utc_datetime_to_display_time_zone_date(self.default_start)
            allocation_objects.allocation.end_date = \
                utc_datetime_to_display_time_zone_date(self.default_end)
            allocation_objects.allocation.save()
            allocation_pks[project.pk] = allocation_objects.allocation.pk

        # Create compute allocations for the Users on the Projects.
        role = ProjectUserRoleChoice.objects.get(name='User')
        for i in range(self.num_users):
            user = User.objects.get(username=f'user{i}')
            project = Project.objects.get(
                name=f'PROJECT_{i // self.num_projects}')
            status = ProjectUserStatusChoice.objects.get(name='Active')
            ProjectUser.objects.create(
                user=user, project=project, role=role, status=status)
            value = Decimal(str(allocation_amount // self.num_projects))
            create_user_project_allocation(user, project, value)

        # Create Jobs with PUT requests.
        index = 12
        dt = self.default_start.replace(
            hour=index, minute=0, second=0, microsecond=0)
        # Jobs were submitted on the hour from 12 to 7 p.m. on the current day.
        for allocation_user in AllocationUser.objects.all():
            for i in range(self.num_projects):
                allocation_amount = int(
                    AllocationUserAttribute.objects.filter(
                        allocation_user=allocation_user).first().value)
                data = {
                    'jobslurmid': str(index),
                    'submitdate': dt.replace(hour=index),
                    'startdate': dt.replace(hour=index),
                    'enddate': dt.replace(hour=index + 1),
                    'userid': UserProfile.objects.get(
                        user=allocation_user.user).cluster_uid,
                    'accountid': allocation_user.allocation.project.name,
                    'amount': str(allocation_amount // self.num_projects),
                    'cpu_time': 1.0,
                }
                url = TestJobList.jobs_put_url(data['jobslurmid'])
                self.client.put(url, data, format='json')
                index = index + 1

        # Reset the client object for testing.
        self.client = APIClient()

    def assert_results(self, url, status_code, count):
        """Assert that making a GET request to the given URL results in
        the given status code. If the status code is 200, assert that
        the number of results (count) is the given one. Return the
        results in a dictionary mapping jobslurmid to the job in
        dictionary form if the status code is 200, else a dictionary of
        errors."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code)
        results_dict = {}
        json = response.json()
        if status_code == 200:
            self.assertEqual(json['count'], count)
            results = json['results']
            for i in range(json['count']):
                result = results[i]
                results_dict[result['jobslurmid']] = result
        else:
            results_dict['errors'] = json
        return results_dict

    @classmethod
    def get_url(cls, **parameters):
        """Return the URL for making a GET request for Jobs with the
        given query filters."""
        base_url = '/api/jobs/'
        separator = '?'
        for parameter in parameters:
            base_url = separator.join(
                [base_url, f'{parameter}={str(parameters[parameter])}'])
            separator = '&'
        return base_url

    def test_no_filters_default_used(self):
        """Test that, when no time filters are provided, only jobs
        within the default period are considered."""
        url = TestJobList.get_url()
        status_code, count = 200, 8
        results_dict = self.assert_results(url, status_code, count)
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertIn('submitdate', job)
            submitdate = datetime.strptime(
                job['submitdate'], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.utc)
            self.assertGreaterEqual(submitdate, self.default_start)
            self.assertLessEqual(submitdate, self.default_end)

    def test_user_filter(self):
        """Test that the user filter filters properly."""
        # There are 8 jobs in total.
        url = TestJobList.get_url()
        status_code, count = 200, 8
        self.assert_results(url, status_code, count)
        # user0 submitted 2 jobs.
        try:
            user = User.objects.get(username='user0')
        except User.DoesNotExist:
            self.fail('A User with username "user" should exist.')
        url = TestJobList.get_url(user=user.username)
        status_code, count = 200, 2
        results_dict = self.assert_results(url, status_code, count)
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertEqual(
                job['userid'], UserProfile.objects.get(user=user).cluster_uid)

    def test_account_filter(self):
        """Test that the account filter filters properly."""
        # There are 8 jobs in total.
        url = TestJobList.get_url()
        status_code, count = 200, 8
        self.assert_results(url, status_code, count)
        # PROJECT_0 submitted 4 jobs.
        try:
            account = Project.objects.get(name='PROJECT_0')
        except Project.DoesNotExist:
            self.fail('A Project with name "PROJECT_0" should exist.')
        url = TestJobList.get_url(account=account.name)
        status_code, count = 200, 4
        results_dict = self.assert_results(url, status_code, count)
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertEqual(job['accountid'], account.name)

    def test_jobstatus_filter(self):
        """Test that the jobstatus filter filters properly."""
        # There are 0 jobs with the jobstatus 'COMPLETED'.
        jobstatus = 'COMPLETED'
        url = TestJobList.get_url(jobstatus=jobstatus)
        status_code, count = 200, 0
        self.assert_results(url, status_code, count)
        # Set the first job's jobstatus to 'COMPLETED'.
        job = Job.objects.first()
        job.jobstatus = jobstatus
        job.save()
        url = TestJobList.get_url(jobstatus=jobstatus)
        status_code, count = 200, 1
        results_dict = self.assert_results(url, status_code, count)
        self.assertEqual(
            results_dict[str(job.jobslurmid)]['jobstatus'], jobstatus)

    def test_amount_filters(self):
        """Test that the min_amount and max_amount filters filter
        properly."""
        status_code = 200
        # All 8 jobs have amount 250.00.
        count = 8
        self.assert_results(
            TestJobList.get_url(min_amount='250'), status_code, count)
        self.assert_results(
            TestJobList.get_url(max_amount='250'), status_code, count)
        self.assert_results(
            TestJobList.get_url(min_amount='250', max_amount='250'),
            status_code, count)
        # Set half of the jobs to have amount 750.00.
        amount = Decimal('750.00')
        n, i = Job.objects.count(), 0
        for job in Job.objects.all():
            if i == n // 2:
                break
            job.amount = amount
            job.save()
            i = i + 1

        # Ensure that various combinations give the expected results.
        minimum, maximum = Decimal(250), Decimal(750)
        results_dict = self.assert_results(
            TestJobList.get_url(min_amount=minimum, max_amount=maximum),
            status_code, 8)
        for jobslurmid in results_dict:
            amount = Decimal(results_dict[jobslurmid]['amount'])
            self.assertTrue(minimum <= amount <= maximum)

        self.assert_results(
            TestJobList.get_url(max_amount=Decimal(249.99)), status_code, 0)

        self.assert_results(
            TestJobList.get_url(min_amount=Decimal(750.01)), status_code, 0)

        maximum = Decimal(500)
        results_dict = self.assert_results(
            TestJobList.get_url(max_amount=maximum), status_code, 4)
        for jobslurmid in results_dict:
            self.assertLessEqual(
                Decimal(results_dict[jobslurmid]['amount']), maximum)

        minimum = Decimal(500)
        results_dict = self.assert_results(
            TestJobList.get_url(min_amount=minimum), status_code, 4)
        for jobslurmid in results_dict:
            self.assertGreaterEqual(
                Decimal(results_dict[jobslurmid]['amount']), minimum)

    def test_partition_filter(self):
        """Test that the partition filter filters properly."""
        # There are 0 jobs with the partition 'PARTITION'.
        partition = 'PARTITION'
        url = TestJobList.get_url(partition=partition)
        status_code, count = 200, 0
        self.assert_results(url, status_code, count)
        # Set the first job's partition to 'PARTITION'.
        job = Job.objects.first()
        job.partition = partition
        job.save()
        url = TestJobList.get_url(partition=partition)
        status_code, count = 200, 1
        results_dict = self.assert_results(url, status_code, count)
        self.assertEqual(
            results_dict[str(job.jobslurmid)]['partition'], partition)

    def test_start_time_filter(self):
        """Test that the start_time filter filters properly."""
        # Four jobs were submitted at or after 4 p.m. today.
        start_dt = self.default_start.replace(
            hour=16, minute=0, second=0, microsecond=0)
        start_time = convert_utc_datetime_to_unix_timestamp(start_dt)
        url = TestJobList.get_url(start_time=start_time)
        status_code, count = 200, 4
        results_dict = self.assert_results(url, status_code, count)
        # Since no end_time was provided, the default should be used.
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertIn('submitdate', job)
            submitdate = datetime.strptime(
                job['submitdate'], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.utc)
            self.assertGreaterEqual(submitdate, start_dt)
            self.assertLessEqual(submitdate, self.default_end)

    def test_invalid_start_time(self):
        """Test that an invalid start time raises an appropriate
        error."""
        url = TestJobList.get_url(start_time='INVALID')
        status_code, count = 400, 0
        errors = self.assert_results(url, status_code, count)['errors']
        self.assertTrue(errors[0].startswith('Invalid starting timestamp'))

    def test_end_time_filter(self):
        """Test that the end_time filter filters properly."""
        # Four jobs were submitted before or at 3 p.m. today.
        end_dt = self.default_start.replace(
            hour=15, minute=0, second=0, microsecond=0)
        end_time = convert_utc_datetime_to_unix_timestamp(end_dt)
        url = TestJobList.get_url(end_time=end_time)
        status_code, count = 200, 4
        results_dict = self.assert_results(url, status_code, count)
        # Since no start_time was provided, the default should be used.
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertIn('submitdate', job)
            submitdate = datetime.strptime(
                job['submitdate'], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.utc)
            self.assertGreaterEqual(submitdate, self.default_start)
            self.assertLessEqual(submitdate, end_dt)

    def test_invalid_end_time(self):
        """Test that an invalid end time raises an appropriate error."""
        url = TestJobList.get_url(end_time='INVALID')
        status_code, count = 400, 0
        errors = self.assert_results(url, status_code, count)['errors']
        self.assertTrue(errors[0].startswith('Invalid ending timestamp'))

    def test_multiple_filters(self):
        """Test that the query filters filter in conjunction."""
        # Six jobs were submitted at or after 1 p.m. and before or at 6 p.m.
        start_dt = self.default_start.replace(
            hour=13, minute=0, second=0, microsecond=0)
        start_time = convert_utc_datetime_to_unix_timestamp(start_dt)
        end_dt = self.default_start.replace(
            hour=18, minute=0, second=0, microsecond=0)
        end_time = convert_utc_datetime_to_unix_timestamp(end_dt)
        url = TestJobList.get_url(start_time=start_time, end_time=end_time)
        status_code, count = 200, 6
        results_dict = self.assert_results(url, status_code, count)
        for jobslurmid in results_dict:
            job = results_dict[jobslurmid]
            self.assertIn('submitdate', job)
            submitdate = datetime.strptime(
                job['submitdate'], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=pytz.utc)
            self.assertGreaterEqual(submitdate, start_dt)
            self.assertLessEqual(submitdate, end_dt)
        # If end_time comes before start_time, no jobs should be returned.
        url = TestJobList.get_url(start_time=end_time, end_time=start_time)
        status_code, count = 200, 0
        self.assert_results(url, status_code, count)

    def test_result_ordering(self):
        """Test that results are returned in ascending submitdate
        order."""
        # Six jobs were submitted at or after 1 p.m. and before or at 6 p.m.
        start_dt = self.default_start.replace(
            hour=13, minute=0, second=0, microsecond=0)
        start_time = convert_utc_datetime_to_unix_timestamp(start_dt)
        end_dt = self.default_start.replace(
            hour=18, minute=0, second=0, microsecond=0)
        end_time = convert_utc_datetime_to_unix_timestamp(end_dt)
        url = TestJobList.get_url(start_time=start_time, end_time=end_time)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertEqual(json['count'], 6)
        jobs = json['results']
        prev_submitdate = datetime.utcfromtimestamp(0)
        for job in jobs:
            self.assertIn('submitdate', job)
            submitdate = datetime.strptime(
                job['submitdate'], "%Y-%m-%dT%H:%M:%SZ")
            self.assertGreaterEqual(submitdate, prev_submitdate)
            prev_submitdate = submitdate

    def test_total_amount_field(self):
        """Test that the sum of the queryset's amounts is included in
        the result."""
        url = TestJobList.get_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertIn('total_amount', json)
        expected_total = Job.objects.aggregate(
            total_amount=Sum('amount'))['total_amount']
        self.assertEqual(Decimal(json['total_amount']), expected_total)

    def test_total_cpu_time_field(self):
        """Test that the sum of the queryset's cpu_times is included in
        the result."""
        url = TestJobList.get_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertIn('total_cpu_time', json)
        expected_total = Job.objects.aggregate(
            total_cpu_time=Sum('cpu_time'))['total_cpu_time']
        self.assertEqual(float(json['total_cpu_time']), expected_total)


class TestJobSerializer(TestJobBase):
    """A suite for testing the functionality of JobSerializer."""

    def assert_error_message(self, data, message):
        """Assert that an error with the given message is raised when
        making a POST request with the given data."""
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('non_field_errors', json)
        self.assertEqual(json['non_field_errors'][0], message)

    def test_required_fields(self):
        """Test that requests fail if required fields are not
        specified."""
        required_fields = ['jobslurmid', 'userid', 'accountid']
        for field in required_fields:
            data = self.data.copy()
            data.pop(field)
            response = self.client.post(self.post_url, data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                'This field is required.', response.json()[field][0])
        self.assertFalse(Job.objects.all())

    def test_non_null_amount(self):
        """Test that requests fail if amount, which cannot be null, is
        specified, but null."""
        data = self.data.copy()
        data['amount'] = None
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            'This field may not be null.', response.json()['amount'][0])
        self.assertFalse(Job.objects.all())

    def test_optional_amount(self):
        """Test that the amount field is optional."""
        data = self.data.copy()
        data.pop('amount')
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['amount'], '0.00')

    def test_invalid_datetime_format(self):
        """Test that requests with improperly formatted dates fail."""
        bad_time = datetime.now().strftime(self.date_format).replace(' ', 'X')
        fields = dict()
        for field in ('submitdate', 'startdate', 'enddate'):
            fields[field] = bad_time
        for field, value in fields.items():
            data = self.data.copy()
            data[field] = value
            response = self.client.post(self.post_url, data, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn(
                'Datetime has wrong format.', response.json()[field][0])
        self.assertFalse(Job.objects.all())

    def test_dates_out_of_order(self):
        """Test that requests fail if specified dates are not
        chronologically ordered."""
        data = self.data.copy()
        data['startdate'] = datetime.now().strftime(self.date_format)
        data['submitdate'] = (datetime.now() + timedelta(seconds=1)).strftime(
            self.date_format)
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('non_field_errors', json)
        message = (
            f'Job start date {data["startdate"]}+00:00 occurs before Job '
            f'submit date {data["submitdate"]}+00:00.')
        self.assertEqual(json['non_field_errors'][0], message)
        data = self.data.copy()
        data['enddate'] = datetime.now().strftime(self.date_format)
        data['startdate'] = (datetime.now() + timedelta(seconds=1)).strftime(
            self.date_format)
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('non_field_errors', json)
        message = (
            f'Job end date {data["enddate"]}+00:00 occurs before Job start '
            f'date {data["startdate"]}+00:00.')
        self.assertEqual(json['non_field_errors'][0], message)
        data = self.data.copy()
        data['enddate'] = datetime.now().strftime(self.date_format)
        data['submitdate'] = (datetime.now() + timedelta(seconds=1)).strftime(
            self.date_format)
        data.pop('startdate')
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('non_field_errors', json)
        message = (
            f'Job end date {data["enddate"]}+00:00 occurs before Job submit '
            f'date {data["submitdate"]}+00:00.')
        self.assertEqual(json['non_field_errors'][0], message)

    def test_invalid_user_id(self):
        """Test that requests with an invalid userid value fail."""
        data = self.data.copy()
        data['userid'] = '1'
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not exist', response.json()['userid'][0])

    def test_invalid_account_id(self):
        """Test that requests with an invalid accountid value fail."""
        data = self.data.copy()
        data['accountid'] = '0'
        response = self.client.post(self.post_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not exist', response.json()['accountid'][0])

    def test_no_user_account_association(self):
        """Test that requests fail with an unrelated user and account
        fail."""
        self.project_user.delete()
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('non_field_errors', json)
        message = (
            f'User {self.user.username} is not a member of account '
            f'{self.project.name}.')
        self.assertEqual(json['non_field_errors'][0], message)

    def test_no_active_compute_allocation(self):
        """Test that requests wherein the account has no active compute
        allocation fail."""
        message = 'Account test_project has no active compute allocation.'
        # The allocation is expired.
        self.allocation.status = AllocationStatusChoice.objects.get(
            name='Expired')
        self.allocation.save()
        self.assert_error_message(self.data, message)
        # The allocation is active, but does not have Savio Compute as a
        # resource.
        self.allocation.status = AllocationStatusChoice.objects.get(
            name='Active')
        self.allocation.resources.all().delete()
        self.allocation.save()
        self.assert_error_message(self.data, message)
        # The allocation does not exist.
        self.allocation.delete()
        self.assert_error_message(self.data, message)

    def test_user_not_member_of_compute_allocation(self):
        """Test that requests wherein the user is not an active member
        of the account's compute allocation fail."""
        message = (
            f'User user0 is not an active member of the compute allocation '
            f'for account test_project.')
        # The allocation user has been removed from the allocation.
        self.allocation_user.status = AllocationUserStatusChoice.objects.get(
            name='Removed')
        self.allocation_user.save()
        self.assert_error_message(self.data, message)
        # The allocation user does not exist.
        self.allocation_user.delete()
        self.assert_error_message(self.data, message)

    def test_bad_database_state_causes_server_error(self):
        """Test that requests fails if there are too few or too many of
        a given database object than expected."""
        message = 'Unexpected server error.'
        # There are multiple allocation user status choices named 'Active'.
        AllocationUserStatusChoice.objects.create(name='Active')
        self.assert_error_message(self.data, message)
        # There are no allocation user status choices named 'Active'.
        AllocationUserStatusChoice.objects.filter(name='Active').delete()
        self.assert_error_message(self.data, message)

    def test_userid_changed_on_put(self):
        """Test that update requests fail if the userid differs from the
        previously set value."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        data = self.data.copy()
        user = User.objects.create(
            username='user1', email='user1@nonexistent.com')
        user_profile = UserProfile.objects.get(user=user)
        user_profile.cluster_uid = '2'
        user_profile.save()

        data['userid'] = UserProfile.objects.get(user=user).cluster_uid
        response = self.client.put(
            TestJobSerializer.put_url(self.data['jobslurmid']), data,
            format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('userid', json)
        message = (
            f'Specified user {user} does not match already associated user '
            f'{self.user}.')
        self.assertEqual(json['userid'][0], message)

    def test_accountid_changed_on_put(self):
        """Test that update requests fail if the accountid differs from
        the previously set value."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        data = self.data.copy()
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name='OTHER_PROJECT', status=project_status)

        data['accountid'] = project.name
        response = self.client.put(
            TestJobSerializer.put_url(self.data['jobslurmid']), data,
            format='json')
        self.assertEqual(response.status_code, 400)
        json = response.json()
        self.assertIn('accountid', json)
        message = (
            f'Specified account {project} does not match already associated '
            f'account {self.project}.')
        self.assertEqual(json['accountid'][0], message)

    # Temporary: Removed while the check is relaxed.
    # def test_partition_changed_on_put(self):
    #     """Test that update requests fail if the partition differs from
    #     the previously set value."""
    #     response = self.client.post(self.post_url, self.data, format='json')
    #     self.assertEqual(response.status_code, 201)
    #     data = self.data.copy()
    #     partition = 'other_partition'
    #     data['partition'] = partition
    #     response = self.client.put(
    #         TestJobSerializer.put_url(self.data['jobslurmid']), data,
    #         format='json')
    #     self.assertEqual(response.status_code, 400)
    #     json = response.json()
    #     self.assertIn('partition', json)
    #     message = (
    #         f'Specified partition {partition} does not match already '
    #         f'associated partition {self.partition}.')
    #     self.assertEqual(json['partition'][0], message)

    # Temporary: Removed while the check is relaxed.
    # def test_qos_changed_on_put(self):
    #     """Test that update requests fail if the partition differs from
    #     the previously set value."""
    #     response = self.client.post(self.post_url, self.data, format='json')
    #     self.assertEqual(response.status_code, 201)
    #     data = self.data.copy()
    #     qos = 'other_qos'
    #     data['qos'] = qos
    #     response = self.client.put(
    #         TestJobSerializer.put_url(self.data['jobslurmid']), data,
    #         format='json')
    #     self.assertEqual(response.status_code, 400)
    #     json = response.json()
    #     self.assertIn('qos', json)
    #     message = (
    #         f'Specified qos {qos} does not match already associated qos '
    #         f'{self.qos}.')
    #     self.assertEqual(json['qos'][0], message)


class TestJobViewSet(TestJobBase):
    """A suite for testing the functionality of JobViewSet."""

    @staticmethod
    def get_usage_values(allocation_objects):
        """
        allocation_objects: object returned by get_accounting_allocation_objects
        with project and user passed as args

        Returns tuple of the allocation and user usage objects
        """
        account_usage = (
            AllocationAttributeUsage.objects.get(
                pk=allocation_objects.allocation_attribute_usage.pk))
        user_account_usage = (
            AllocationUserAttributeUsage.objects.get(
                pk=allocation_objects.allocation_user_attribute_usage.pk))

        return account_usage, user_account_usage

    def test_unauthorized_post_denied(self):
        """Test that unauthorized POST requests from non-staff accounts
        are denied."""
        self.client = APIClient()
        # The user must provide an authorization token.
        response = self.client.post(self.post_url, data={})
        self.assertEqual(response.status_code, 401)
        json = response.json()
        self.assertEqual(
            json['detail'], 'Authentication credentials were not provided.')
        # The user must have the is_staff field set to True.
        user = User.objects.create(username='user1')
        token = ExpiringToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.post(self.post_url, data={})
        self.assertEqual(response.status_code, 403)
        json = response.json()
        message = 'You do not have permission to perform this action.'
        self.assertEqual(json['detail'], message)

    def test_unauthorized_put_denied(self):
        """Test that unauthorized PUT requests from non-staff accounts
        are denied."""
        self.client = APIClient()
        # The user must provide an authorization token.
        response = self.client.put(self.put_url(1), data={})
        self.assertEqual(response.status_code, 401)
        json = response.json()
        self.assertEqual(
            json['detail'], 'Authentication credentials were not provided.')
        # The user must have the is_staff field set to True.
        user = User.objects.create(username='user1')
        token = ExpiringToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.put(self.put_url(1), data={})
        self.assertEqual(response.status_code, 403)
        json = response.json()
        message = 'You do not have permission to perform this action.'
        self.assertEqual(json['detail'], message)

    def test_get(self):
        """Test that jobs are returned from a GET request."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        response = self.client.get(self.get_url)
        json = response.json()
        self.assertEqual(len(json['results']), 1)
        job = json['results'][0]
        self.assertEqual(job['jobslurmid'], self.data['jobslurmid'])
        for field in ('submitdate', 'startdate', 'enddate'):
            self.assertEqual(
                job[field].replace('T', ' ').replace('Z', ''),
                self.data[field])
        self.assertEqual(job['userid'], self.data['userid'])
        self.assertEqual(job['accountid'], self.data['accountid'])
        self.assertEqual(job['amount'], self.data['amount'])

    def test_get_by_jobslurmid(self):
        """Test that a single job can be retrieved from a GET
        request."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        response = self.client.get(TestJobViewSet.put_url(1))
        self.assertEqual(response.status_code, 200)
        job = response.json()
        self.assertEqual(job['jobslurmid'], self.data['jobslurmid'])
        for field in ('submitdate', 'startdate', 'enddate'):
            self.assertEqual(
                job[field].replace('T', ' ').replace('Z', ''),
                self.data[field])
        self.assertEqual(job['userid'], self.data['userid'])
        self.assertEqual(job['accountid'], self.data['accountid'])
        self.assertEqual(job['amount'], self.data['amount'])

    def test_post(self):
        """Test that fields set during a POST (create) request are saved
        correctly."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        job = Job.objects.get(jobslurmid=self.data['jobslurmid'])
        self.assertEqual(job.jobslurmid, self.data['jobslurmid'])
        for field in ('submitdate', 'startdate', 'enddate'):
            self.assertEqual(
                getattr(job, field).strftime(self.date_format),
                self.data[field])
        self.assertEqual(job.userid, self.user)
        self.assertEqual(job.accountid, self.project)
        self.assertEqual(job.amount, Decimal(self.data['amount']))
        self.assertEqual(job.jobstatus, self.job_status)
        self.assertEqual(job.partition, self.partition)
        self.assertEqual(job.qos, self.qos)

    def test_post_duplicate(self):
        """Test that POST (create) requests with an existing ID fail."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Job.objects.count(), 1)
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Job.objects.count(), 1)

    def test_patch_job_not_supported(self):
        """Test that PATCH (partial update) requests are not
        supported."""
        response = self.client.patch(
            TestJobViewSet.put_url('1'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertIn('failure', json)
        self.assertEqual(json['failure'], 'This method is not supported.')

    def test_put(self):
        """Test that only those fields set during a PUT (update) request
        are updated."""
        response = self.client.post(self.post_url, self.data, format='json')
        self.assertEqual(response.status_code, 201)
        job = Job.objects.get(jobslurmid=self.data['jobslurmid'])
        data = self.data.copy()
        data['enddate'] = datetime.now().strftime(self.date_format)
        data['amount'] = str(Decimal(data['amount']) + Decimal('100.00'))
        response = self.client.put(
            TestJobViewSet.put_url(self.data['jobslurmid']), data,
            format='json')
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.jobslurmid, self.data['jobslurmid'])
        for field in ('submitdate', 'startdate'):
            self.assertEqual(
                getattr(job, field).strftime(self.date_format),
                self.data[field])
        self.assertEqual(
            job.enddate.strftime(self.date_format), data['enddate'])
        self.assertEqual(job.userid, self.user)
        self.assertEqual(job.accountid, self.project)
        self.assertEqual(job.amount, Decimal(data['amount']))
        self.assertEqual(job.jobstatus, self.job_status)
        self.assertEqual(job.partition, self.partition)
        self.assertEqual(job.qos, self.qos)

    def test_put_creates_if_nonexistent(self):
        """Test that a PUT (update) request creates the target object if
        it does not already exist."""
        response = self.client.put(
            TestJobViewSet.put_url(self.data['jobslurmid']), self.data,
            format='json')
        self.assertEqual(response.status_code, 200)
        job = Job.objects.get(jobslurmid=self.data['jobslurmid'])
        self.assertEqual(job.jobslurmid, self.data['jobslurmid'])
        for field in ('submitdate', 'startdate', 'enddate'):
            self.assertEqual(
                getattr(job, field).strftime(self.date_format),
                self.data[field])
        self.assertEqual(job.userid, self.user)
        self.assertEqual(job.accountid, self.project)
        self.assertEqual(job.amount, Decimal(self.data['amount']))
        self.assertEqual(job.jobstatus, self.job_status)
        self.assertEqual(job.partition, self.partition)
        self.assertEqual(job.qos, self.qos)

    def test_optional_amount_skips_usage(self):
        """Test that, if amount is not specified, usages are not
        updated."""
        account_usage = AllocationAttributeUsage.objects.first()
        user_account_usage = AllocationUserAttributeUsage.objects.first()

        data = self.data.copy()
        data.pop('amount')
        response = self.client.post(
            TestJobViewSet.post_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        job = Job.objects.get(jobslurmid=self.data['jobslurmid'])
        self.assertEqual(job.amount, Decimal('0.00'))
        account_usage.refresh_from_db()
        user_account_usage.refresh_from_db()
        self.assertEqual(account_usage.value, Decimal('0.00'))
        self.assertEqual(user_account_usage.value, Decimal('0.00'))
        response = self.client.put(
            TestJobViewSet.put_url(data['jobslurmid']), data, format='json')
        self.assertEqual(response.status_code, 200)

        job = Job.objects.get(jobslurmid=self.data['jobslurmid'])
        self.assertEqual(job.amount, Decimal('0.00'))
        account_usage.refresh_from_db()
        user_account_usage.refresh_from_db()
        self.assertEqual(account_usage.value, Decimal('0.00'))
        self.assertEqual(user_account_usage.value, Decimal('0.00'))

    def test_other_requests_not_allowed(self):
        """Test that other requests (e.g. DELETE; POST/PUT to the wrong
        URL) are not allowed."""
        self.assertEqual(
            self.client.post(TestJobViewSet.put_url('1')).status_code, 405)
        self.assertEqual(self.client.put(self.post_url).status_code, 405)
        self.assertEqual(self.client.delete(self.post_url).status_code, 405)
        self.assertEqual(self.client.delete(self.post_url).status_code, 405)

    def test_post_invalid_job_start_date(self):
        """Test that a POST (create) request does not update usages if
        the job's start date is before the allocation's start date."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Set the Job's submitdate and startdate to be within the Allocation's
        # start_date and end_date. Set its enddate to be 5 days after the
        # Allocation's end_date.
        data['submitdate'] = (allocation_objects.allocation.start_date -
                              timedelta(days=6)).strftime(self.date_format)
        data['startdate'] = (allocation_objects.allocation.start_date -
                             timedelta(days=5)).strftime(self.date_format)

        response = self.client.post(
            TestJobViewSet.post_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should not have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertEqual(pre_allocation_usage, allocation_usage.value)
        self.assertEqual(pre_user_usage, user_usage.value)

    def test_post_invalid_job_end_date(self):
        """Test that POST (create) request does update usages if the job
        unexpectedly has an end date, and it is after the allocation's
        end date."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Set the Job's submitdate and startdate to be within the Allocation's
        # start_date and end_date. Set its enddate to be 5 days after the
        # Allocation's end_date.
        data['submitdate'] = (allocation_objects.allocation.start_date +
                              timedelta(days=4)).strftime(self.date_format)
        data['startdate'] = (allocation_objects.allocation.start_date +
                             timedelta(days=5)).strftime(self.date_format)
        data['enddate'] = (allocation_objects.allocation.end_date +
                           timedelta(days=5)).strftime(self.date_format)

        response = self.client.post(
            TestJobViewSet.post_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertLess(pre_allocation_usage, allocation_usage.value)
        self.assertLess(pre_user_usage, user_usage.value)

    def test_post_job_missing_dates(self):
        """Test that a POST (create) request does not update usages if
        the job is missing submit or start dates."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Remove Job dates, one at a time.
        for date in ['submitdate', 'startdate']:
            popped_date = data.pop(date)

            response = self.client.post(
                TestJobViewSet.post_url, data, format='json')
            self.assertEqual(response.status_code, 201)

            # A Job should have been created.
            self.assertTrue(
                Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

            # Usages should not have been updated.
            allocation_usage.refresh_from_db()
            user_usage.refresh_from_db()
            self.assertEqual(pre_allocation_usage, allocation_usage.value)
            self.assertEqual(pre_user_usage, user_usage.value)

            # Reset data for the next test.
            data[date] = popped_date
            Job.objects.get(jobslurmid=data['jobslurmid']).delete()
            self.assertFalse(
                Job.objects.filter(jobslurmid=data['jobslurmid']).exists())
            allocation_usage.value = pre_allocation_usage
            allocation_usage.save()
            user_usage.value = pre_user_usage
            user_usage.save()

    def test_post_allocation_missing_dates(self):
        """Test that a POST (create) request conditionally updates
        usages based on which date its Allocation is missing. In
        particular, for any allocation type, iff the start date is
        missing, usages should not be updated."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])

        allocation_types = ('ac_', 'co_', 'fc_', 'ic_', 'pc_')
        for allocation_type in allocation_types:
            project.name = f'{allocation_type}{project.name[3:]}'
            project.save()
            project.refresh_from_db()
            data['accountid'] = project.name
            allocation_objects = get_accounting_allocation_objects(
                project, user)

            allocation_usage, user_usage = self.get_usage_values(
                allocation_objects)
            allocation_usage.value = Decimal('0.00')
            allocation_usage.save()
            user_usage.value = Decimal('0.00')
            user_usage.save()

            pre_allocation_usage, pre_user_usage = \
                allocation_usage.value, user_usage.value

            for date in ['start_date', 'end_date']:
                # Remove the date.
                original_date = getattr(allocation_objects.allocation, date)
                setattr(allocation_objects.allocation, date, None)
                allocation_objects.allocation.save()
                self.assertIsNone(getattr(allocation_objects.allocation, date))

                response = self.client.post(
                    TestJobViewSet.post_url, data, format='json')
                self.assertEqual(response.status_code, 201)

                # A Job should have been created.
                self.assertTrue(
                    Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

                # Usage should not have been updated if the start_date was
                # removed, but not if the end_date was removed.
                allocation_usage.refresh_from_db()
                user_usage.refresh_from_db()
                if date == 'start_date':
                    self.assertEqual(
                        pre_allocation_usage, allocation_usage.value)
                    self.assertEqual(
                        pre_user_usage, user_usage.value)
                else:
                    self.assertLess(
                        pre_allocation_usage, allocation_usage.value)
                    self.assertLess(
                        pre_user_usage, user_usage.value)

                # Reset the date.
                setattr(allocation_objects.allocation, date, original_date)
                allocation_objects.allocation.save()

                # Delete the Job for the next test.
                Job.objects.get(jobslurmid=data['jobslurmid']).delete()
                self.assertFalse(
                    Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

    @patch('coldfront.api.statistics.views.JobViewSet.validate_job_dates')
    def test_post_handles_exception_when_validating_dates(self, mock_method):
        """Test that a POST (create) request does not fail to create a
        job even if an exception is raised when determining whether
        dates are valid."""
        # Patch the method for validating dates to raise an exception.
        def raise_exception(*args, **kwargs):
            raise Exception('Test exception.')
        mock_method.side_effect = raise_exception

        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        with self.assertLogs('coldfront.api.statistics.views', 'ERROR') as cm:
            response = self.client.post(
                TestJobViewSet.post_url, data, format='json')
        self.assertEqual(response.status_code, 201)

        all_log_output = '\n'.join(cm.output)
        self.assertIn(
            (f'Failed to determine whether dates for Job {data["jobslurmid"]} '
             f'are valid.'),
            all_log_output)
        self.assertIn('Test exception.', all_log_output)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should not have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertEqual(pre_allocation_usage, allocation_usage.value)
        self.assertEqual(pre_user_usage, user_usage.value)

    def test_put_invalid_job_start_date(self):
        """Test that a PUT (update) request does not update usages if
        the job's start date is before the allocation's start date."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Set the Job's submitdate and startdate to be before the Allocation's
        # start_date.
        data['submitdate'] = (allocation_objects.allocation.start_date -
                              timedelta(days=6)).strftime(self.date_format)
        data['startdate'] = (allocation_objects.allocation.start_date -
                             timedelta(days=5)).strftime(self.date_format)

        response = self.client.put(
            TestJobViewSet.put_url(data['jobslurmid']), data,
            format='json')
        self.assertEqual(response.status_code, 200)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should not have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertEqual(pre_allocation_usage, allocation_usage.value)
        self.assertEqual(pre_user_usage, user_usage.value)

    def test_put_invalid_job_end_date(self):
        """Test that a PUT (update) request does not update usages if
        the job's end date is after the allocation's end date."""
        data = self.data.copy()
        project = Project.objects.get(name=data['accountid'])
        new_project_name = f'fc_{data["accountid"]}'
        project.name = new_project_name
        project.save()
        data['accountid'] = new_project_name

        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Set the Job's submitdate and startdate to be within the Allocation's
        # start_date and end_date. Set its enddate to be 5 days after the
        # Allocation's end_date.
        data['submitdate'] = (allocation_objects.allocation.start_date +
                              timedelta(days=4)).strftime(self.date_format)
        data['startdate'] = (allocation_objects.allocation.start_date +
                             timedelta(days=5)).strftime(self.date_format)
        data['enddate'] = (allocation_objects.allocation.end_date +
                           timedelta(days=5)).strftime(self.date_format)

        response = self.client.put(
            TestJobViewSet.put_url(data['jobslurmid']), data,
            format='json')
        self.assertEqual(response.status_code, 200)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should not have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertEqual(pre_allocation_usage, allocation_usage.value)
        self.assertEqual(pre_user_usage, user_usage.value)

    def test_put_job_missing_dates(self):
        """Test that a PUT (update) request does not update usages if
        the job does not have a start or end date."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        # Remove Job dates, one at a time.
        for date in ['submitdate', 'startdate', 'enddate']:
            popped_date = data.pop(date)
            response = self.client.put(
                TestJobViewSet.put_url(data['jobslurmid']), data,
                format='json')
            self.assertEqual(response.status_code, 200)

            response = self.client.put(
                TestJobViewSet.put_url(data['jobslurmid']), data,
                format='json')
            self.assertEqual(response.status_code, 200)

            # A Job should have been created.
            self.assertTrue(
                Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

            # Usages should not have been updated.
            allocation_usage.refresh_from_db()
            user_usage.refresh_from_db()
            self.assertEqual(pre_allocation_usage, allocation_usage.value)
            self.assertEqual(pre_user_usage, user_usage.value)

            # Reset data for the next test.
            data[date] = popped_date
            Job.objects.get(jobslurmid=data['jobslurmid']).delete()
            allocation_usage.value = pre_allocation_usage
            allocation_usage.save()
            user_usage.value = pre_user_usage
            user_usage.save()

    def test_put_allocation_missing_dates(self):
        """Test that a PUT (update) request conditionally updates usages
        based on which date its Allocation is missing and the Project's
        allocation type. In particular, for any allocation type, if the
        start date is missing, or the end date is missing and the
        allocation type is one expected to have an end date, usages
        should not be updated."""
        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])

        allocation_types = ('ac_', 'co_', 'fc_', 'ic_', 'pc_')
        allocation_types_with_end_dates = {'fc_', 'ic_', 'pc_'}
        for allocation_type in allocation_types:
            project.name = f'{allocation_type}{project.name[3:]}'
            project.save()
            project.refresh_from_db()
            data['accountid'] = project.name
            allocation_objects = get_accounting_allocation_objects(
                project, user)

            allocation_usage, user_usage = self.get_usage_values(
                allocation_objects)
            allocation_usage.value = Decimal('0.00')
            allocation_usage.save()
            user_usage.value = Decimal('0.00')
            user_usage.save()

            pre_allocation_usage, pre_user_usage = \
                allocation_usage.value, user_usage.value

            for date in ['start_date', 'end_date']:
                # Remove the date.
                original_date = getattr(allocation_objects.allocation, date)
                setattr(allocation_objects.allocation, date, None)
                allocation_objects.allocation.save()
                self.assertIsNone(getattr(allocation_objects.allocation, date))

                response = self.client.put(
                    TestJobViewSet.put_url(data['jobslurmid']), data,
                    format='json')
                self.assertEqual(response.status_code, 200)

                # A Job should have been created.
                self.assertTrue(
                    Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

                # Usages should not have been updated if the start_date was
                # removed, or if the end_date was removed and it was expected
                # to be there.
                allocation_usage.refresh_from_db()
                user_usage.refresh_from_db()
                if (date == 'start_date' or
                        (date == 'end_date' and
                         allocation_type in allocation_types_with_end_dates)):
                    self.assertEqual(
                        pre_allocation_usage, allocation_usage.value)
                    self.assertEqual(pre_user_usage, user_usage.value)
                else:
                    self.assertLess(
                        pre_allocation_usage, allocation_usage.value)
                    self.assertLess(
                        pre_user_usage, user_usage.value)

                # Reset the date.
                setattr(allocation_objects.allocation, date, original_date)
                allocation_objects.allocation.save()

                # Delete the Job for the next test.
                Job.objects.get(jobslurmid=data['jobslurmid']).delete()
                self.assertFalse(
                    Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

    @patch('coldfront.api.statistics.views.JobViewSet.validate_job_dates')
    def test_put_handles_exception_when_validating_dates(self, mock_method):
        """Test that a PUT (update) request does not fail to create a
        job even if an exception is raised when determining whether
        dates are valid."""
        # Patch the method for validating dates to raise an exception.
        def raise_exception(*args, **kwargs):
            raise Exception('Test exception.')
        mock_method.side_effect = raise_exception

        data = self.data.copy()
        user = UserProfile.objects.get(cluster_uid=data['userid']).user
        project = Project.objects.get(name=data['accountid'])
        allocation_objects = get_accounting_allocation_objects(project, user)

        allocation_usage, user_usage = self.get_usage_values(
            allocation_objects)

        pre_allocation_usage, pre_user_usage = \
            allocation_usage.value, user_usage.value

        with self.assertLogs('coldfront.api.statistics.views', 'ERROR') as cm:
            response = self.client.put(
                TestJobViewSet.put_url(data['jobslurmid']), data,
                format='json')
        self.assertEqual(response.status_code, 200)

        all_log_output = '\n'.join(cm.output)
        self.assertIn(
            (f'Failed to determine whether dates for Job {data["jobslurmid"]} '
             f'are valid.'),
            all_log_output)
        self.assertIn('Test exception.', all_log_output)

        # A Job should have been created.
        self.assertTrue(
            Job.objects.filter(jobslurmid=data['jobslurmid']).exists())

        # Usages should not have been updated.
        allocation_usage.refresh_from_db()
        user_usage.refresh_from_db()
        self.assertEqual(pre_allocation_usage, allocation_usage.value)
        self.assertEqual(pre_user_usage, user_usage.value)
