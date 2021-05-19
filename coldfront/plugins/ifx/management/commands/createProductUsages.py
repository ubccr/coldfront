# -*- coding: utf-8 -*-

'''
Create ProductUsages and AllocationUserProductUsages from AllocationUsers for a specified month
'''
from io import StringIO
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.core.management import call_command
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import AllocationUser, Allocation
from coldfront.plugins.ifx.models import allocation_user_to_allocation_product_usage


class Command(BaseCommand):
    '''
    Create ProductUsages and AllocationUserProductUsages from AllocationUsers for a specified month
    '''
    help = 'Create ProductUsages for the given year and month.  Use --overwrite to remove existing records and recreate. Usage:\n' + \
        "./manage.py createProductUsages --year 2021 --month 3"

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

    def handle(self, *args, **kwargs):
        month = int(kwargs['month'])
        year = int(kwargs['year'])
        overwrite = kwargs['overwrite']

        successes = 0
        errors = []
        for resource in Resource.objects.filter(requires_payment=True):
            products = resource.productresource_set.all()
            if len(products) == 1:
                product = products[0]

                # Get the AllocationUser records
                allocations = Allocation.object.filter(resources__in=[resource])
                for allocation in allocations:
                    for allocation_user in AllocationUser.objects.filter(allocation=allocation, updated__month=month, updated__year=year):
                        try:
                            allocation_user_to_allocation_product_usage(allocation_user, product, overwrite)
                        except Exception as e:
                            errors.append(f'Error creating product usage for {product} and user {allocation_user.user}: {e}')
            else:
                errors.append(f'Unable to fine a Product for resource {resource}')


