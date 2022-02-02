from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create group for staff with all necessary permissions.'

    def handle(self, *args, **options):
        new_group, created = Group.objects.get_or_create(name='staff_group')

        if not created:
            new_group.permissions.clear()

        perm_codename_lst = [
            'view_allocationadditionrequest',
            'view_allocationrenewalrequest',
            'view_vectorprojectallocationrequest',
            'view_savioprojectallocationrequest',
            'can_review_cluster_account_requests',
            'can_review_pending_project_reviews',
            'can_view_all_allocations',
            'can_view_all_projects',
            'view_projectuserjoinrequest',
            'view_projectuserremovalrequest',
            'view_job',
        ]

        for perm_codename in perm_codename_lst:
            try:
                permission = Permission.objects.get(codename=perm_codename)
                new_group.permissions.add(permission)
            except Permission.DoesNotExist:
                raise LookupError('Queried permission does not exist. Examine '
                                  'core/utils/management/commands/create_staff_group.py')

        # Send a joined list of permissions to a command-line output.
        self.stdout.write('Created staff group and permissions.')

