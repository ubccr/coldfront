# -*- coding: utf-8 -*-

'''
Update nanites PersonAffiliations using coldfront allocation user data
'''
import logging
import re
from django.core.management.base import BaseCommand
from ifxuser.models import IfxUser
from nanites.client import API as NanitesAPI

logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Update nanites PersonAffiliations using coldfront allocation user data
    '''
    help = 'Add affiliations to Nanites Persons using Coldfront allocation user data. Usage:\n' + \
        './manage.py updateAffiliations [--verbose]'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Report full exception trace',
        )

    def handle(self, *args, **kwargs):
        '''
        For each user in the system, get their allocation user information and push affiliation updates to Nanites
        '''
        verbose = kwargs['verbose']
        slug_clean_re = re.compile(r' \([^\)]+\)')

        total_processed = 0
        total_added = 0
        errors = []
        affiliations = {}
        count = IfxUser.objects.count()
        print(f'Processing {count} total Coldfront users')
        for ifxuser in IfxUser.objects.all():
            for au in ifxuser.allocationuser_set.filter(allocation__status__name='Active'):
                ifxid = ifxuser.ifxid
                if ifxid:
                    if ifxid not in affiliations:
                        affiliations[ifxid] = set()
                    for org in au.allocation.project.projectorganization_set.all():
                        affiliations[ifxid].add(org.organization)
        for ifxid in sorted(affiliations.keys()):
            try:
                person = NanitesAPI.readPerson(ifxid=ifxid)
                added = []
                for allocation_affiliation in affiliations[ifxid]:
                    found = False
                    for affiliation in person.affiliations:
                        if allocation_affiliation.slug == affiliation.slug:
                            found = True
                    if not found:
                        print(f'Did not find {allocation_affiliation.slug} in existing affiliations for {ifxid}')
                        added.append(
                            {
                                'active': True,
                                'role': 'member',
                                'slug': allocation_affiliation.slug,
                            }
                        )
                if added:
                    for added_affiliation in added:
                        person.affiliations.append(added_affiliation)
                        total_added += 1
                    comment_str = ', '.join([re.sub(slug_clean_re, '', a['slug']) for a in added])
                    change_comment = f'Added affiliation to {comment_str} based on Coldfront data'
                    person.change_comment = change_comment[:255]
                    NanitesAPI.updatePerson(**person.to_dict())

            except Exception as e:
                if verbose:
                    logger.exception(e)
                errors.append(str(e))

            total_processed += 1

        print(f'{total_processed} allocation users successfully processed\n{total_added} new affiliation(s) added')

        if errors:
            print(f'Errors:\n')
            print('\n'.join(errors))
