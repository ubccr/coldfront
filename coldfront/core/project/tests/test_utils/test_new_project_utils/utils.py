from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.user.models import UserProfile

from django.contrib.auth.models import User


class TestRunnerMixinBase(object):
    """A base mixin for testing runners."""

    def setUp(self):
        """Set up tests data."""
        super().setUp()
        self.allocation_period = get_current_allowance_year_period()

        # Create a requester user and a PI user.
        self.requester = User.objects.create(
            email='requester@email.com',
            first_name='Requester',
            last_name='User',
            username='requester')
        self.pi = User.objects.create(
            email='pi@email.com',
            first_name='PI',
            last_name='User',
            username='pi')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create a Project.
        active_project_status = ProjectStatusChoice.objects.get(name='New')
        self.project = Project.objects.create(
            name='fc_project', status=active_project_status)
