import datetime
import os
import pprint

from django.conf import settings
from django.core.management.base import BaseCommand

from core.djangoapps.publication.models import Publication, PublicationStatusChoice
from core.djangoapps.project.models import Project, ProjectStatusChoice

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):

        Publication.objects.all().delete()

        delimiter = '\t'
        file_path = os.path.join(base_dir, 'local_data', 'publications.tsv')


        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                created, modified, publication__project__title, publication__project__status, publication__project__pi__username, publication__title, publication__author, publication__doi, publication__full_citation, publication__status = line.strip().split(delimiter)

                created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
                modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')


                project_obj = Project.objects.get(
                    title=publication__project__title,
                    status__name=publication__project__status,
                    pi__username=publication__project__pi__username
                )

                publication_status_obj = PublicationStatusChoice.objects.get(name=publication__status)
                publication_obj, created = Publication.objects.get_or_create(
                    created=created,
                    modified=modified,
                    project=project_obj,
                    title=publication__title,
                    author=publication__author,
                    doi=publication__doi,
                    full_citation=publication__full_citation,
                    status=publication_status_obj
                )
