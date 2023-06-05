from django.core.management.base import BaseCommand

from coldfront.plugins.ldap.utils import collect_update_project_status_membership

class Command(BaseCommand):
    """
    Update ProjectUsers for active Projects using ADGroup and ADUser data
    """

    def handle(self, *args, **kwargs):
        collect_update_project_status_membership()
