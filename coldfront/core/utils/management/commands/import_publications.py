import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)
from coldfront.core.publication.models import Publication, PublicationSource

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding publications ...')
        # delimiter = chr(255)
        delimiter = '\t'
        file_path = os.path.join(base_dir, 'local_data', 'publications_combined.tsv')
        Publication.objects.all().delete()

        doi_source = PublicationSource.objects.get(name='doi')

        with open(file_path, 'r') as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue

                created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi = line.split(delimiter)

                created = datetime.datetime.strptime(created.split('.')[0], '%m/%d/%Y')
                # created = '{}-{}-{}'.format(created.year, created.month, created.day)
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
                    print('Violate unique constraint')
                    print(created, modified, project_title, project_status, pi_username, publication_title, author, journal, publication_year, doi)


        print('Finished adding publications')
