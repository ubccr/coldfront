from django.core.management import call_command

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

base_dir = settings.BASE_DIR

class Command(BaseCommand):

    def handle(self, *args, **options):

        call_command('import_field_of_science_data')
        call_command('add_default_grant_options')
        call_command('add_default_project_choices')
        call_command('add_default_subscription_choices')
        call_command('import_users')
        call_command('import_projects')
        call_command('import_resources')
        call_command('import_subscriptions')
        call_command('import_grants')
