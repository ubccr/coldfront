from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser


class Command(BaseCommand):

    help = 'Verify that data loaded into the LRC service are correct.'

    def handle(self, *args, **options):
        self.assert_projects_have_pis()
        self.assert_user_profile_is_pi_consistent_with_project_pis()

    def assert_user_profile_is_pi_consistent_with_project_pis(self):
        user_pks_with_pi_status = set(
            User.objects.filter(userprofile__is_pi=True).values_list('pk'))
        seen_users = set()

        project_users = ProjectUser.objects.filter(
            role__name='Principal Investigator')
        for project_user in project_users.iterator():
            user_pk = project_user.user.pk
            if user_pk in seen_users:
                continue
            if user_pk in user_pks_with_pi_status:
                user_pks_with_pi_status.remove(user_pk)
                seen_users.add(user_pk)
                continue
            message = (
                f'ProjectUser {project_user.pk} is a PI, but the User does '
                f'not have is_pi status.')
            self.stderr.write(self.style.ERROR(message))

        if user_pks_with_pi_status:
            message = (
                f'Users {sorted(user_pks_with_pi_status)} have is_pi status, '
                f'but are not PIs of Projects.')
            self.stderr.write(self.style.ERROR(message))

    def assert_projects_have_pis(self):
        for project in Project.objects.iterator():
            if not project.pis().exists():
                message = f'Project {project.name} has no PIs.'
                self.stderr.write(self.style.ERROR(message))

    def assert_pis_have_at_most_one_pca(self):
        pass
