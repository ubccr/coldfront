'''
Custom billing calculator class for Coldfront
'''
import logging
from functools import reduce
from decimal import Decimal
from django.db import connection
from ifxbilling.calculator import BasicBillingCalculator


logger = logging.getLogger(__name__)


class ColdfrontBillingCalculator(BasicBillingCalculator):
    '''
    Calculate and collect Allocation fractions so that billing can reflect the percentage of the Allocation used
    '''
    def getRateDescription(self, rate):
        '''
        Text description of rate for use in txn rate and description.
        Empty string is returned if rate.price or rate.units is None.
        '''
        desc = ''
        if rate.price is not None and rate.units is not None:
            dollar_price = Decimal(rate.price) / 100
            desc = f'${dollar_price.quantize(Decimal(".01"))} per {rate.units}'
        return desc

    def getAllocationFromProductUsage(self, product_usage):
        '''
        Returns the relevant Allocation
        '''
        # There should be only one!
        allocation_user_product_usage = product_usage.allocationuserproductusage_set.first()
        return allocation_user_product_usage.allocation_user.allocation

    def calculateCharges(self, product_usage, percent, usage_data):
        '''
        Check for the Allocation information in the usage_data dictionary.  If it's there, use the
        fractions to figure out the charge.  If not, get the other AllocationUser data to calculate
        the fractions and save in the usage_data dict.
        '''
        allocation = self.getAllocationFromProductUsage(product_usage)
        if allocation.id not in usage_data:
            usage_data[allocation.id] = self.calculateAllocationUserFractions(product_usage)

        allocation_user_fractions = usage_data[allocation.id]

        product = product_usage.product
        rate = product.rate_set.get(is_active=True)
        if rate.units != 'TB':
            raise Exception(f'Units for {product} should be "TB"')
        if product_usage.units != 'b':
            raise Exception('Product usage units should be in bytes (b)')

        rate_desc = self.getRateDescription(rate)

        transactions_data = []

        # Get the quota.  Charge will be users percent of quota value.
        quota_attribute = allocation.allocationattribute_set.filter(allocation_attribute_type__name='Storage Quota (TB)').first()
        try:
            quota = Decimal(quota_attribute.value)
        except ValueError:
            raise ValueError(f'Storage quota value for {allocation} cannot be converted to a float.')

        try:
            product_user_percent = allocation_user_fractions[product_usage.product_user.id]['fraction']
        except Exception as e:
            raise Exception(f'Allocation user fractions dict has no percent value for {product_usage.product_user} {product_usage.product_user.id}: {allocation_user_fractions}')

        percent_str = ''
        if percent < 100:
            percent_str = f'a {percent}% split of '
        dollar_price = Decimal(rate.price) / 100

        # Round Decimal charge to nearest integer (pennies)
        charge = round(Decimal(rate.price) * quota * product_user_percent * percent / 100)
        dollar_charge = Decimal(charge / 100).quantize(Decimal("100.00"))

        description = f'${dollar_charge} for {percent_str}{product_user_percent.quantize(Decimal("100.000")) * 100}% of {quota} TB at ${dollar_price.quantize(Decimal(".01"))} per {rate.units}'
        user = product_usage.product_user

        transactions_data.append(
            {
                'charge': charge,
                'description': description,
                'author': user,
                'rate': rate_desc,
            }
        )
        return transactions_data

    def calculateAllocationUserFractions(self, product_usage):
        '''
        Get the allocation and then get all of the AllocationProductUsages and ProductUsages associated
        with it for the same year / month.  Calculate fraction for each user and return.
        '''

        # Of the form
        # allocation_user_fractions = {
        #    <allocation id>: {
        #        <allocation user id 1>: {
        #           'fraction': 0.2,
        #           'quantity': 2000
        #        }
        #        <allocation user id 2>: {
        #            'fraction': 0.8,
        #            'quantity': 8000
        #        }
        #    }
        # }

        allocation = self.getAllocationFromProductUsage(product_usage)
        allocation_user_fractions = {}

        sql = '''
            select
                pu.product_user_id, sum(pu.quantity)
            from
                product_usage pu inner join ifx_allocationuserproductusage aupu on pu.id = aupu.product_usage_id
                inner join allocation_historicalallocationuser hau on hau.history_id = aupu.allocation_user_id
                inner join allocation_allocation a on a.id = hau.allocation_id
                inner join user_account ua on ua.user_id = pu.product_user_id
            where
                hau.allocation_id = %s
                and pu.year = %s
                and pu.month = %s
            group by pu.product_user_id
        '''.replace('\n', ' ')

        cursor = connection.cursor()
        cursor.execute(sql, [allocation.id, product_usage.year, product_usage.month])
        total = 0
        for row in cursor.fetchall():
            allocation_user_fractions[row[0]] = {
                'quantity': row[1]
            }
            total += row[1]
        for uid in allocation_user_fractions.keys():
            allocation_user_fractions[uid]['fraction'] = Decimal(allocation_user_fractions[uid]['quantity']) / Decimal(total)

        logger.debug('Allocation user fractions %s', str(allocation_user_fractions))
        return allocation_user_fractions

    def createBillingRecordForUsage(self, product_usage, account, percent, year=None, month=None, description=None, usage_data=None):
        '''
        Run base class method then update BillingRecord description to combination of transaction descriptions
        '''
        billing_record = super().createBillingRecordForUsage(product_usage, account, percent, year, month, description, usage_data)
        # Join the transaction descriptions
        description = '\n'.join([trxn.description for trxn in billing_record.transaction_set.all()])
        billing_record.description = description
        billing_record.save()
        return billing_record