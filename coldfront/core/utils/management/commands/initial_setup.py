import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

base_dir = settings.BASE_DIR


class Command(BaseCommand):
    help = 'Run setup script to initialize Coldfront with testing data'

    def add_arguments(self, parser):
         parser.add_argument("-fo", "--force-overwrite", help="Force intial_setup script to run with no warning.")

    def handle(self, *args, **options):
            if options['force-overwrite']:
                call_command('migrate')
                call_command('import_field_of_science_data')
                call_command('add_default_grant_options')
                call_command('add_default_project_choices')
                call_command('add_resource_defaults')
                call_command('add_allocation_defaults')
                call_command('add_default_publication_sources')
                call_command('add_scheduled_tasks')

            else:
                print("""WARNING: Running this command initializes the ColdFront database. This should only be run one time. Running this will delete anything currently in the ColdFront database.""")
                user_response = input("Do you want to proceed?(yes):")
            
                if user_response == "yes":
                    call_command('migrate')
                    call_command('import_field_of_science_data')
                    call_command('add_default_grant_options')
                    call_command('add_default_project_choices')
                    call_command('add_resource_defaults')
                    call_command('add_allocation_defaults')
                    call_command('add_default_publication_sources')
                    call_command('add_scheduled_tasks')
                else:
                    print("Please enter 'yes' if you wish to run intital setup.")
                
        
