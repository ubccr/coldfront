import os

from django.core.management.base import BaseCommand

from coldfront.core.publication.models import PublicationSource


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        PublicationSource.objects.all().delete()
        for name, url in [
                ('doi', 'https://doi.org/'),
                ('orcid', 'https://orcid.org/'), #Added
                ('manual', None),
            ]:
            PublicationSource.objects.get_or_create(name=name, url=url)
