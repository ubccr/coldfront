import os

from django.core.management.base import BaseCommand

from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.config.defaults import GRANT_DEFAULTS as defaults

app_dir = os.path.dirname(__file__)


class Command(BaseCommand):
    def handle(self, *args, **options):

        GrantFundingAgency.objects.all().delete()
        for choice in defaults['fundingagencies']:
            GrantFundingAgency.objects.get_or_create(name=choice)

        GrantStatusChoice.objects.all().delete()
        for choice in defaults['statuschoices']:
            GrantStatusChoice.objects.get_or_create(name=choice)
