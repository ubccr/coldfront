from django.core.management.base import BaseCommand

from coldfront.core.publication.models import PublicationSource
from coldfront.config.defaults import PUBLICATION_DEFAULTS as defaults


class Command(BaseCommand):
    help = 'Add default project related choices'

    def handle(self, *args, **options):
        PublicationSource.objects.all().delete()
        for name, url in defaults['publicationsources']:
            PublicationSource.objects.get_or_create(name=name, url=url)
