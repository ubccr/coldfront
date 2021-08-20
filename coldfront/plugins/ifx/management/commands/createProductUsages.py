# -*- coding: utf-8 -*-

'''
Create ProductUsages and AllocationUserProductUsages from AllocationUsers for a specified month
'''
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import AllocationUser, Allocation
from coldfront.plugins.ifx.models import allocation_user_to_allocation_product_usage

logger = logging.getLogger('')

class Command(BaseCommand):
    '''
    Create ProductUsages and AllocationUserProductUsages from AllocationUsers for a specified month
    '''
    help = 'Create ProductUsages for the given year and month.  Use --overwrite to remove existing records and recreate. Usage:\n' + \
        './manage.py createProductUsages --year 2021 --month 3\n\n' + \
        'Use --select-year and --select-month to use allocation information from a different month / year.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            dest='year',
            default=timezone.now().year,
            help='Year for calculation',
        )
        parser.add_argument(
            '--month',
            dest='month',
            default=timezone.now().month,
            help='Month for calculation',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Remove existing product usages',
        )
        parser.add_argument(
            '--select-year',
            dest='select_year',
            help='Select allocation data from this year if different from --year',
        )
        parser.add_argument(
            '--select-month',
            dest='select_month',
            help='Select allocation data from this month if different from --month',
        )

    def handle(self, *args, **kwargs):
        month = select_month = int(kwargs['month'])
        year = select_year = int(kwargs['year'])
        if 'select_month' in kwargs and kwargs['select_month']:
            select_month = int(kwargs['select_month'])
        if 'select_year' in kwargs and kwargs['select_year']:
            select_year = int(kwargs['select_year'])

        overwrite = kwargs['overwrite']
        successes = 0
        errors = []
        for resource in Resource.objects.filter(requires_payment=True):
            product_resources = resource.productresource_set.all()
            if len(product_resources) == 1:
                product = product_resources[0].product

                # Get the AllocationUser records
                allocations = Allocation.objects.filter(resources__in=[resource], status__name='Active')
                print(f'Processing {len(allocations)} allocations for {resource}')
                for allocation in allocations:
                    for allocation_user in AllocationUser.objects.filter(allocation=allocation, modified__month=select_month, modified__year=select_year):
                        try:
                            allocation_user_to_allocation_product_usage(allocation_user, product, overwrite, month=month, year=year)
                            successes += 1
                        except Exception as e:
                            if 'AllocationUserProductUsage already exists for use of' not in str(e):
                                logger.exception(e)
                            errors.append(f'Error creating product usage for {product} and user {allocation_user.user}: {e}')
            else:
                errors.append(f'Unable to fine a Product for resource {resource}')
        print(f'{successes} records successfully created.')
        if errors:
            print('Errors: %s' % "\n".join(errors))
        logger.debug('Done')

