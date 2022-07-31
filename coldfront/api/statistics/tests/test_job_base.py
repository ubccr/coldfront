from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.api.utils.tests.test_api_base import TestAPIBase
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User


class TestJobBase(TestAPIBase):
    """A base class for testing Job-related functionality."""

    date_format = '%Y-%m-%d %H:%M:%S'
    get_url = post_url = '/api/jobs/'

    @classmethod
    def put_url(cls, jobslurmid):
        """Return the URL for making a PUT request to the Job identified
        by the given jobslurmid."""
        return f'{cls.post_url}{jobslurmid}/'

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a User and a PI.
        self.user = User.objects.create(
            username='user0', email='user0@nonexistent.com')
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.cluster_uid = '0'
        self.user_profile.save()
        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create a Project and ProjectUsers.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        self.project = Project.objects.create(
            name='fc_project', status=project_status)
        status = ProjectUserStatusChoice.objects.get(name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        self.project_user = ProjectUser.objects.create(
            user=self.user, project=self.project, role=user_role,
            status=status)
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        ProjectUser.objects.create(
            user=self.pi, project=self.project, role=manager_role,
            status=status)

        # Get the start and end times of the current Allowance Year.
        current_allowance_year_period = get_current_allowance_year_period()
        period_start_date = current_allowance_year_period.start_date
        period_end_date = current_allowance_year_period.end_date
        self.default_start = display_time_zone_date_to_utc_datetime(
            period_start_date)
        self.default_end = display_time_zone_date_to_utc_datetime(
            period_end_date) + timedelta(hours=24) - timedelta(microseconds=1)

        # Create a "CLUSTER_NAME Compute" Allocation for the Project.
        allocation_objects = create_project_allocation(
            self.project, Decimal('1000.00'))
        self.allocation = allocation_objects.allocation
        self.allocation.start_date = period_start_date
        self.allocation.end_date = period_end_date
        self.allocation.save()
        self.allocation_attribute = allocation_objects.allocation_attribute
        self.account_usage = AllocationAttributeUsage.objects.first()

        # Create a compute allocation for the User on the Project.
        allocation_objects = create_user_project_allocation(
            self.user, self.project, Decimal('500.00'))
        self.allocation_user = allocation_objects.allocation_user
        self.allocation_user_attribute = \
            allocation_objects.allocation_user_attribute
        self.user_account_usage = AllocationUserAttributeUsage.objects.first()

        # Create foreign key objects needed for Job creation.
        self.job_status = 'test_job_status'
        self.partition = 'test_partition'
        self.qos = 'test_qos'

        # Set up request data.
        jobslurmid = '1'
        amount = '100.00'
        submitdate = datetime.now().strftime(self.date_format)
        startdate = datetime.now().strftime(self.date_format)
        enddate = datetime.now().strftime(self.date_format)
        self.data = {
            'jobslurmid': jobslurmid,
            'submitdate': submitdate,
            'startdate': startdate,
            'enddate': enddate,
            'userid': UserProfile.objects.get(user=self.user).cluster_uid,
            'accountid': self.project.name,
            'amount': amount,
            'jobstatus': self.job_status,
            'partition': self.partition,
            'qos': self.qos
        }
