# -*- coding: utf-8 -*-

'''
Calculate billing records for the given year and month
'''
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from ifxbilling.models import Facility
from coldfront.plugins.ifx.calculator import NewColdfrontBillingCalculator


logger = logging.getLogger('ifxbilling')


class Command(BaseCommand):
    '''
    Calculate billing records for the given year and month
    '''
    help = 'Calculate billing records for the given year and month.  Use --recalculate to remove existing records and recreate. Usage:\n' + \
        "./manage.py calculateBillingRecords --year 2021 --month 3"

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
            '--recalculate',
            action='store_true',
            help='Remove existing billing records and recalculate',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Report full exception for errors',
        )
        parser.add_argument(
            '--facility-name',
            dest='facility_name',
            help='Name of the facility to calculate for.  Can be omitted if there is only one Facility record.'
        )
        parser.add_argument(
            '--product-names',
            dest='product_names',
            help='Comma-separated list of product names.'
        )

    def handle(self, *args, **kwargs):
        month = int(kwargs['month'])
        year = int(kwargs['year'])
        recalculate = kwargs['recalculate']
        bc = NewColdfrontBillingCalculator()
        (successes, errors) = bc.calculate_billing_month(month, year, recalculate=recalculate)

        print(f'{successes} product usages successfully processed')
        if errors:
            print('Errors: %s' % '\n'.join(errors))
