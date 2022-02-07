import csv
import datetime
import json
from csv import DictReader

import pytz
from django.db.models import F, Func, Value, CharField
from django.test import TestCase

from django.contrib.auth.models import User, Group
from django.core.management import call_command, CommandError

from io import StringIO
import os
import sys

from coldfront.config import settings
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestBase2(TestBase):
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

        self.job1 = Job.objects.create(jobslurmid='12345',
                                       submitdate=self.current_time - datetime.timedelta(days=5),
                                       startdate=self.current_time - datetime.timedelta(days=4),
                                       enddate=self.current_time - datetime.timedelta(days=3),
                                       userid=self.user1)

        self.job2 = Job.objects.create(jobslurmid='98765',
                                       submitdate=self.current_time - datetime.timedelta(days=12),
                                       startdate=self.current_time - datetime.timedelta(days=10),
                                       enddate=self.current_time - datetime.timedelta(days=9),
                                       userid=self.user1)


class TestUserList(TestBase2):
    """ Test class to test export data subcommand user_list runs correctly """

    def setUp(self):
        """Setup test data"""
        super().setUp()

    def test_user_list_json_no_date(self):
        """Testing user_list subcommand with NO date arg passed,
        exporting as JSON"""
        Job.objects.create(jobslurmid='33333',
                           submitdate=self.current_time - datetime.timedelta(days=1),
                           startdate=self.current_time - datetime.timedelta(days=2),
                           enddate=self.current_time - datetime.timedelta(days=3),
                           userid=self.user2)

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=json',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))

        job_list = Job.objects.annotate(submit_date=Func(
            F('submitdate'),
            Value('MM-dd-yyyy hh:mm:ss'),
            function='to_char',
            output_field=CharField()),
            username=F('userid__username')).\
            order_by('userid', '-submitdate').distinct('userid').\
            values('username', 'jobslurmid', 'submit_date')

        for index, item in enumerate(output):
            self.assertDictEqual(item, job_list[index])

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

        job_list = Job.objects.annotate(submit_date=Func(
            F('submitdate'),
            Value('MM-dd-yyyy hh:mm:ss'),
            function='to_char',
            output_field=CharField()),
            username=F('userid__username')). \
            order_by('userid', '-submitdate').distinct('userid'). \
            values('username', 'jobslurmid', 'submit_date').\
            get(jobslurmid='12345')

        for index, item in enumerate(output):
            self.assertDictEqual(item, job_list)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_user_list_csv_no_date(self):
        """Testing user_list subcommand with NO date arg passed,
        exporting as CSV"""
        Job.objects.create(jobslurmid='33333',
                           submitdate=self.current_time - datetime.timedelta(days=1),
                           startdate=self.current_time - datetime.timedelta(days=2),
                           enddate=self.current_time - datetime.timedelta(days=3),
                           userid=self.user2)

        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'user_list', '--format=csv',
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = csv.reader(out.readlines())

        job_list = Job.objects.annotate(submit_date=Func(
            F('submitdate'),
            Value('MM-dd-yyyy hh:mm:ss'),
            function='to_char',
            output_field=CharField()),
            username=F('userid__username')).\
            order_by('userid', '-submitdate').distinct('userid').\
            values_list('username', 'jobslurmid', 'submit_date')

        for index, item in enumerate(reader):
            if index == 0:
                lst = ['username', 'jobslurmid', 'submit_date']
            else:
                lst = list(job_list[index-1])

            self.assertEqual(item, lst)

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

        job_list = Job.objects.annotate(submit_date=Func(
            F('submitdate'),
            Value('MM-dd-yyyy hh:mm:ss'),
            function='to_char',
            output_field=CharField()),
            username=F('userid__username')). \
            order_by('userid', '-submitdate').distinct('userid'). \
            values_list('username', 'jobslurmid', 'submit_date').\
            get(jobslurmid='12345')

        for index, item in enumerate(reader):
            if index == 0:
                lst = ['username', 'jobslurmid', 'submit_date']
            else:
                lst = list(job_list)

            self.assertEqual(item, lst)

        err.seek(0)
        self.assertEqual(err.read(), '')


# class TestNewUserAccount(TestBase2):
#     """Test class to test export data subcommand new_user_account runs
#     correctly."""
#
#     def setUp(self):
#         """Setup test data"""
#         super().setUp()
#
#     def convert_time_to_utc(self, time):
#         """Convert naive LA time to UTC time"""
#         local_tz = pytz.timezone('America/Los_Angeles')
#         tz = pytz.timezone(settings.TIME_ZONE)
#         naive_dt = datetime.datetime.combine(time, datetime.datetime.min.time())
#         new_time = local_tz.localize(naive_dt).astimezone(tz).isoformat()
#
#         return new_time
#
#     def test_test_new_user_account_json_no_date(self):
#         """Testing new_user_account subcommand with NO date arg passed,
#         exporting as JSON"""
#
#         out, err = StringIO(''), StringIO('')
#         call_command('export_data', 'new_user_account', '--format=json',
#                      stdout=out, stderr=err)
#         sys.stdout = sys.__stdout__
#
#         out.seek(0)
#         output = json.loads(''.join(out.readlines()))
#
#         cluster_account_status = AllocationAttributeType.objects.get(
#             name='Cluster Account Status')
#
#         user_list = AllocationUserAttribute.objects.filter(
#             allocation_attribute_type=cluster_account_status,
#             value='Active')
#
#         user_list = User.objects.annotate(
#             date_created=Func(
#                 F('created'),
#                 Value('MM-dd-yyyy hh:mm:ss'),
#                 function='to_char',
#                 output_field=CharField()),
#             username=F('allocation_user__user__username')).\
#             order_by('username', '-created'). \
#             distinct('username').values('username', 'date_created')
#
#         for index, item in enumerate(output):
#             self.assertDictEqual(item, user_list[index])
#
#         err.seek(0)
#         self.assertEqual(err.read(), '')
#
#     def test_test_new_user_account_json_with_date(self):
#         """Testing new_user_account subcommand with ONE date arg passed,
#         exporting as JSON"""
#
#         start_date = datetime.datetime.strftime(
#             self.current_time - datetime.timedelta(days=4), '%m-%d-%Y')
#
#         new_date = self.convert_time_to_utc(self.current_time -
#                                             datetime.timedelta(days=10))
#         self.user2.date_joined = new_date
#         self.user2.save()
#         self.assertEqual(self.user2.date_joined, new_date)
#
#         out, err = StringIO(''), StringIO('')
#         call_command('export_data', 'new_user_account', '--format=json',
#                      f'--date={start_date}', stdout=out, stderr=err)
#         sys.stdout = sys.__stdout__
#
#         out.seek(0)
#         output = json.loads(''.join(out.readlines()))
#
#         user_list = User.objects.annotate(str_date_joined=Func(
#             F('date_joined'),
#             Value('MM-dd-yyyy hh:mm:ss'),
#             function='to_char',
#             output_field=CharField()
#         )).order_by('username', '-date_joined'). \
#             distinct('username').values('username', 'str_date_joined').get(
#             username=self.user1.username
#         )
#
#         for index, item in enumerate(output):
#             self.assertDictEqual(item, user_list)
#
#         err.seek(0)
#         self.assertEqual(err.read(), '')
#
#     def test_test_new_user_account_csv_no_date(self):
#         """Testing new_user_account subcommand with NO date arg passed,
#         exporting as CSV"""
#
#         out, err = StringIO(''), StringIO('')
#         call_command('export_data', 'new_user_account', '--format=csv',
#                      stdout=out, stderr=err)
#         sys.stdout = sys.__stdout__
#
#         out.seek(0)
#         reader = csv.reader(out.readlines())
#
#         user_list = User.objects.annotate(str_date_joined=Func(
#             F('date_joined'),
#             Value('MM-dd-yyyy hh:mm:ss'),
#             function='to_char',
#             output_field=CharField()
#         )).order_by('username', '-date_joined'). \
#             distinct('username').values_list('username', 'str_date_joined')
#
#         for index, item in enumerate(reader):
#             if index == 0:
#                 lst = ['username', 'str_date_joined']
#             else:
#                 lst = list(user_list[index-1])
#
#             self.assertEqual(item, lst)
#
#             err.seek(0)
#             self.assertEqual(err.read(), '')
#
#     def test_test_new_user_account_csv_with_date(self):
#         """Testing new_user_account subcommand with ONE date arg passed,
#         exporting as CSV"""
#         start_date = datetime.datetime.strftime(
#             self.current_time - datetime.timedelta(days=4), '%m-%d-%Y')
#
#         new_date = self.convert_time_to_utc(self.current_time -
#                                             datetime.timedelta(days=10))
#         self.user2.date_joined = new_date
#         self.user2.save()
#         self.assertEqual(self.user2.date_joined, new_date)
#
#         out, err = StringIO(''), StringIO('')
#         call_command('export_data', 'new_user_account', '--format=csv',
#                      f'--date={start_date}', stdout=out, stderr=err)
#         sys.stdout = sys.__stdout__
#
#         out.seek(0)
#         reader = csv.reader(out.readlines())
#
#         user_list = User.objects.annotate(str_date_joined=Func(
#             F('date_joined'),
#             Value('MM-dd-yyyy hh:mm:ss'),
#             function='to_char',
#             output_field=CharField()
#         )).order_by('username', '-date_joined'). \
#             distinct('username').values_list('username', 'str_date_joined').get(
#             username=self.user1.username
#         )
#
#         for index, item in enumerate(reader):
#             if index == 0:
#                 lst = ['username', 'str_date_joined']
#             else:
#                 lst = list(user_list)
#
#             self.assertEqual(item, lst)
#
#             err.seek(0)
#             self.assertEqual(err.read(), '')


class TestJobAvgQueueTime(TestBase2):
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

        self.assertIn('36hrs 0mins 0secs', out.read())

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
