'''
Custom billing calculator class for Coldfront
'''
import logging
from django.db import connection
from ifxbilling.calculator import BasicBillingCalculator


logger = logging.getLogger(__name__)


class ColdfrontBillingCalculator(BasicBillingCalculator):
    '''
    Calculate and collect Allocation percentages so that billing can reflect the percentage of the Allocation used
    '''
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
        percentages to figure out the charge.  If not, get the other AllocationUser data to calculate
        the percentages and save in the usage_data dict.
        '''
        allocation = self.getAllocationFromProductUsage(product_usage)
        if allocation.id not in usage_data:
            usage_data[allocation.id] = self.calculateAllocationUserPercentages(product_usage)

        allocation_user_percentages = usage_data[allocation.id]

        product = product_usage.product
        rate = product.rate_set.get(is_active=True)
        if rate.units != product_usage.units:
            raise Exception(f'Units for product usage do not match the active rate for {product}')
        transactions_data = []

        # Get the quota.  Charge will be users percent of quota value.
        quota_attribute = allocation.allocationattribute_set.filter(allocation_attribute_type__name='Storage Quota (TB)').first()
        try:
            quota = float(quota_attribute.value)
        except ValueError:
            raise ValueError(f'Storage quota value for {allocation} cannot be converted to a float.')

        try:
            product_user_percent = allocation_user_percentages[product_usage.product_user.id]['percent']
        except Exception as e:
            raise Exception(f'Allocation user percentages dict has no percent value for {product_usage.product_user} {product_usage.product_user.id}: {allocation_user_percentages}')

        percent_str = ''
        if percent < 100:
            percent_str = f'{percent}% split of '
        description = f'{percent_str}{product_user_percent}% of {quota} TB at {rate.price} per {rate.units}'

        charge = round(rate.price * quota * product_user_percent * percent / 100)
        user = product_usage.product_user

        transactions_data.append(
            {
                'charge': charge,
                'description': description,
                'author': user
            }
        )
        return transactions_data

    def calculateAllocationUserPercentages(self, product_usage):
        '''
        Get the allocation and then get all of the AllocationProductUsages and ProductUsages associated
        with it for the same year / month.  Calculate percentage for each user and return.
        '''

        # Of the form
        # allocation_user_percentages = {
        #    <allocation id>: {
        #        <allocation user id 1>: {
        #           'percent': 20,
        #           'quantity': 2000
        #        }
        #        <allocation user id 2>: {
        #            'percent': 80,
        #            'quantity': 8000
        #        }
        #    }
        # }

        allocation = self.getAllocationFromProductUsage(product_usage)
        allocation_user_percentages = {}

        sql = '''
            select
                pu.product_user_id, sum(pu.quantity)
            from
                product_usage pu inner join ifx_allocationuserproductusage aupu on pu.id = aupu.product_usage_id
                inner join allocation_historicalallocationuser hau on hau.history_id = aupu.allocation_user_id
                inner join allocation_allocation a on a.id=hau.allocation_id
            where
                hau.allocation_id = %s
                and pu.year = %s
                and pu.month = %s
            group by pu.product_user_id
        '''.replace('\n', ' ')

        cursor = connection.cursor()
        rows = cursor.execute(sql, [allocation.id, product_usage.year, product_usage.month])
        logger.error('Rows is %s', str(rows))
        total = 0
        for row in rows:
            logger.error('product_user_id %d, quantity %d', row[0], row[1])
            allocation_user_percentages[row[0]] = {
                'quantity': row[1]
            }
            total += row[1]
        for uid in allocation_user_percentages.keys():
            allocation_user_percentages[uid]['percent'] = allocation_user_percentages[uid]['quantity'] / total * 100

        logger.error('Allocation user percentages %s', str(allocation_user_percentages))
        return allocation_user_percentages
