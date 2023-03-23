import os

from django.core.management.base import BaseCommand

from coldfront.core.publication.models import PublicationSource
from coldfront.core.utils.common import import_from_settings
PUBLICATION_ENABLE = import_from_settings('PUBLICATION_ENABLE', False)

if PUBLICATION_ENABLE:
    class Command(BaseCommand):
        help = 'Add default project related choices'

        def handle(self, *args, **options):
            PublicationSource.objects.all().delete()
            for name, url in [
                    ('doi', 'https://doi.org/'),
                    ('manual', None),
                ]:
                PublicationSource.objects.get_or_create(name=name, url=url)
