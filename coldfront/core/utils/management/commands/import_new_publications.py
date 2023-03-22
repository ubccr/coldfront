import datetime
import os
import csv
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.publication.models import Publication, PublicationSource

class Command(BaseCommand):
    help="Add Publications"

    def add_arguments(self, parser):
        parser.add_argument("-i","--input",help=help)
        return super().add_arguments(parser)
    def handle(self, *args, **options):
        # base_dir = settings.BASE_DIR
        # filename = os.path.join(base_dir, 'local_data', '-i')
        filename=options["input"]
    def import_publications(filename):
        print('Adding publications ...')
        doi_source = PublicationSource.objects.get(name='doi')

        with open(filename) as file:
            next(file)
            f=csv.reader(file)
            for line in f:
        
                created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi = line

                created = datetime.datetime.strptime(created.split('.')[0], '%m/%d/%Y')
                modified = datetime.datetime.strptime(modified.split('.')[0], '%m/%d/%Y').strftime('%Y-%m-%d')
                project_obj = Project.objects.get(pi__username=pi_username, title=project_title, status__name=project_status)

                try:
                    Publication.objects.get_or_create(
                        created=created,
                        modified=modified,
                        project=project_obj,
                        title=publication_title.encode("ascii", errors="ignore").decode(),
                        author=author.encode("ascii", errors="ignore").decode(),
                        journal=author.encode("ascii", errors="ignore").decode(),
                        year=publication_year,
                        unique_id=doi,
                        source=doi_source
                    )
                except Exception as e:
                    print(e)
                    print('Violated unique constraint')
                    print(created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi)


        print('Publications Added!')
