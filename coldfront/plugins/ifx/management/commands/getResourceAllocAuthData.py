# -*- coding: utf-8 -*-

'''
Get data for resource allocation authorization mapping
'''
import logging
from django.core.management.base import BaseCommand
from coldfront.plugins.ifx.models import get_resource_allocation_authorization_map
logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Get data for resource allocation authorization mapping
    '''
    help = 'Get data for resource allocation authorization mapping. Usage:\n' + \
        './manage.py getResourceAllocAuthData'


    def handle(self, *args, **kwargs):
        '''
        Get all of the Organizations in the Research Computing AD tree
        '''
        print(get_resource_allocation_authorization_map())
