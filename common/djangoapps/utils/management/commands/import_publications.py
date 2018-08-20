import datetime
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from common.djangoapps.field_of_science.models import FieldOfScience
from core.djangoapps.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)

from core.djangoapps.publication.models import Publication

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding publications ...')
        # delimiter = chr(255)
        delimiter = '\t'
        file_path = os.path.join(base_dir, 'local_data', 'publications_with_verified_doi.tsv')
        Publication.objects.all().delete()

        with open(file_path, 'r') as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue

                created, modified, project_title, project_status, pi_username, publication_title, author, publication_date, doi = line.split(delimiter)

                created = datetime.datetime.strptime(created.split('.')[0], '%m/%d/%Y')
                # created = '{}-{}-{}'.format(created.year, created.month, created.day)
                modified = datetime.datetime.strptime(modified.split('.')[0], '%m/%d/%Y').strftime('%Y-%m-%d')
                publication_date = datetime.datetime.strptime(publication_date, '%m/%d/%Y')
                # modified = '{}-{}-{}'.format(modified.year, modified.month, modified.day)
                print(created, modified, project_title, project_status, pi_username, publication_title, author, publication_date, doi)

                project_obj = Project.objects.get(pi__username=pi_username, title=project_title, status__name=project_status)

                Publication.objects.get_or_create(
                    created=created,
                    modified=modified,
                    project=project_obj,
                    title=publication_title.encode("ascii", errors="ignore").decode(),
                    author=author.encode("ascii", errors="ignore").decode(),
                    publication_date=publication_date,
                    unique_id=doi

                )

        print('Finished adding publications')
