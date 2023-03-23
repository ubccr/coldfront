import os

from django.core.management.base import BaseCommand

from coldfront.core.grant.models import GrantFundingAgency, GrantStatusChoice
from coldfront.core.utils.common import import_from_settings
GRANT_ENABLE = import_from_settings('GRANT_ENABLE', False)

app_dir = os.path.dirname(__file__)

if GRANT_ENABLE:
    class Command(BaseCommand):
        def handle(self, *args, **options):

            GrantFundingAgency.objects.all().delete()
            for choice in [
                    'Department of Defense (DoD)',
                    'Department of Energy (DOE)',
                    'Environmental Protection Agency (EPA)',
                    'National Aeronautics and Space Administration (NASA)',
                    'National Institutes of Health (NIH)',
                    'National Science Foundation (NSF)',
                    'New York State Department of Health (DOH)',
                    'New York State (NYS)',
                    'Empire State Development (ESD)',
                    "Empire State Development's Division of Science, Technology and Innovation (NYSTAR)",
                    'Other'
                ]:
                GrantFundingAgency.objects.get_or_create(name=choice)

            GrantStatusChoice.objects.all().delete()
            for choice in ['Active', 'Archived', 'Pending', ]:
                GrantStatusChoice.objects.get_or_create(name=choice)
