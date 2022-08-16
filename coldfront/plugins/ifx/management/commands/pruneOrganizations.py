# -*- coding: utf-8 -*-

'''
Prune organizations that are not associated with a Project to speed up billing record retrieval
'''
import logging
from django.core.management.base import BaseCommand
from ifxuser.models import Organization
from requests import delete

logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Prune organizations that are not associated with a Project to speed up billing record retrieval
    '''
    help = 'Prune Organizations that are not associated with a Project. Usage:\n' + \
        './manage.py pruneOrganizations\n\n'

    def handle(self, *args, **kwargs):
        deleted_count = 0
        for organization in Organization.objects.all():
            if not organization.projectorganization_set.count():
                try:
                    organization.delete()
                    deleted_count += 1
                except Exception:
                    # If there is an error (ie has primary affiliation references), just move on
                    pass
        print(f'{deleted_count} organizations removed')
