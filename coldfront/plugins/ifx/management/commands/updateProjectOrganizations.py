# -*- coding: utf-8 -*-

'''
Update ProjectOrganization records from Nanites Organization "sisters"
'''
import logging
from django.core.management.base import BaseCommand
from ifxuser.models import Organization
from coldfront.core.project.models import Project
from coldfront.plugins.ifx.models import ProjectOrganization
from nanites.client import API as NanitesAPI

logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Update ProjectOrganization records from Nanites Organization "sisters"
    '''
    help = 'Update ProjectOrganization records from Nanites Organization "sisters". Usage:\n' + \
        './manage.py updateProjectOrganizations'


    def handle(self, *args, **kwargs):
        '''
        Get all of the Organizations in the Research Computing AD tree
        '''
        successes = 0
        errors = []
        for rc_sister in NanitesAPI.getRcSisters():
            try:
                project = Project.objects.get(title=rc_sister.rc)
                organization = Organization.objects.get(ifxorg=rc_sister.harvard)
                po, created = ProjectOrganization.objects.get_or_create(project=project, organization=organization)
                successes += 1
            except Project.DoesNotExist:
                errors.append(f'Unable to find project {rc_sister.rc}')
            except Organization.DoesNotExist:
                errors.append(f'Unable to find organization {rc_sister.harvard} to go with {rc_sister.rc}')
        print(f'{successes} RC / Harvard mappings successfully processed')
        if (errors):
            print('Errors')
            print('\n'.join(errors))
