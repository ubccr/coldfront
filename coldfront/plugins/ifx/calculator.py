'''
Custom billing calculator class for Coldfront
'''
import logging
from collections import defaultdict
from decimal import Decimal
from django.db import connection
from django.utils import timezone
from django.contrib.auth import get_user_model
from ifxbilling.calculator import BasicBillingCalculator
from ifxbilling.models import Account, Product, ProductUsage
from coldfront.core.allocation.models import Allocation


logger = logging.getLogger(__name__)


class ColdfrontBillingCalculator(BasicBillingCalculator):
    '''
    Calculate and collect Allocation fractions so that billing can reflect the percentage of the Allocation used
    '''
    def __init__(self):
        '''
        Setup a structure for calculating offer letter charges
        '''
        self.allocation_offer_letters = defaultdict(dict)
        for allocation in Allocation.objects.all():
            offer_letter_tb = allocation.get_attribute('Offer Letter')
            if offer_letter_tb:
                self.allocation_offer_letters[allocation.id]['offer_letter_tb'] = offer_letter_tb
            offer_letter_code = allocation.get_attribute('Offer Letter Code')
            if offer_letter_code:
                self.allocation_offer_letters[allocation.id]['offer_letter_code'] = offer_letter_code


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

        user = product_usage.product_user

        # Round Decimal charge to nearest integer (pennies)
        charge = round(Decimal(rate.price) * quota * product_user_percent * percent / 100)

        if charge == 0:
            raise Exception('No billing record for $0 charges')

        # Check for offer letter.  If so, remove the percent of the allocation represented by the offer letter and add to an accumulating charge.
        # For example, if allocation is 2Tb and offer letter is 1Tb, remove half of the charge for this usage and apply to the offer_letter_charge
        offer_letter_data = self.allocation_offer_letters.get(allocation.id)
        if offer_letter_data:
            try:
                allocation_subsidy_percent = int(offer_letter_data['offer_letter_tb']) / quota
            except ValueError:
                raise Exception(f'Cannot convert offer_letter_tb {offer_letter_data["offer_letter_tb"]} to an integer')
            if allocation_subsidy_percent > 1:
                allocation_subsidy_percent = 1
            allocation_subsidy = charge * allocation_subsidy_percent
            if 'offer_letter_charge' in self.allocation_offer_letters[allocation.id]:
                self.allocation_offer_letters[allocation.id]['offer_letter_charge'] += allocation_subsidy
            else:
                self.allocation_offer_letters[allocation.id]['offer_letter_charge'] = allocation_subsidy
            self.allocation_offer_letters[allocation.id]['year'] = product_usage.year
            self.allocation_offer_letters[allocation.id]['month'] = product_usage.month
            self.allocation_offer_letters[allocation.id]['rate'] = rate
            transactions_data.append(
                {
                    'charge': allocation_subsidy * -1,
                    'description': 'Offer letter subsidy',
                    'author': user,
                    'rate': rate_desc,
                }
            )

        dollar_charge = Decimal(charge / 100).quantize(Decimal("100.00"))

        description = f'${dollar_charge} for {percent_str}{product_user_percent.quantize(Decimal("100.000")) * 100}% of {quota} TB at ${dollar_price.quantize(Decimal(".01"))} per {rate.units}'

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

        # Sum the quantity of usage for users that have user_accounts or user_product_accounts
        # with an organization that matches the project organization mapping
        # The UNION combines the user_accounts and the user_product_accounts
        sql = '''
            select product_user_id, sum(quantity)
            from (
                select
                    pu.product_user_id, sum(pu.quantity) as quantity
                from
                    product_usage pu inner join ifx_allocationuserproductusage aupu on pu.id = aupu.product_usage_id
                    inner join allocation_historicalallocationuser hau on hau.history_id = aupu.allocation_user_id
                    inner join allocation_allocation a on a.id = hau.allocation_id
                where
                    hau.allocation_id = %s
                    and pu.year = %s
                    and pu.month = %s
                    and exists (
                        select 1
                        from
                            user_account ua inner join account acct on ua.account_id = acct.id
                            inner join ifx_projectorganization po on acct.organization_id = po.organization_id
                        where
                            po.project_id = a.project_id
                            and ua.user_id = pu.product_user_id
                            and ua.is_valid = 1
                    )
                group by pu.product_user_id
                union
                select
                    pu.product_user_id, sum(pu.quantity) as quantity
                from
                    product_usage pu inner join ifx_allocationuserproductusage aupu on pu.id = aupu.product_usage_id
                    inner join allocation_historicalallocationuser hau on hau.history_id = aupu.allocation_user_id
                    inner join allocation_allocation a on a.id = hau.allocation_id
                where
                    hau.allocation_id = %s
                    and pu.year = %s
                    and pu.month = %s
                    and exists (
                        select 1
                        from
                            user_product_account ua inner join account acct on ua.account_id = acct.id
                            inner join ifx_projectorganization po on acct.organization_id = po.organization_id
                        where
                            po.project_id = a.project_id
                            and ua.user_id = pu.product_user_id
                            and ua.is_valid = 1
                    )
                group by pu.product_user_id
            ) t
            group by product_user_id
        '''.replace('\n', ' ')

        cursor = connection.cursor()
        cursor.execute(sql, [allocation.id, product_usage.year, product_usage.month, allocation.id, product_usage.year, product_usage.month])
        total = 0
        count = 0
        for row in cursor.fetchall():
            allocation_user_fractions[row[0]] = {
                'quantity': row[1]
            }
            total += row[1]
            count += 1

        if total == 0 and count == 0:
            raise Exception(f'Allocation {allocation} of usage {product_usage} has no user at all.  This should be impossible.')

        for uid in allocation_user_fractions.keys():
            # For the situation where there is an allocation, and the PI is an allocation user, but no data is used
            # set fraction to 1 / count where count is probably just one.
            if total == 0:
                allocation_user_fractions[uid]['fraction'] = Decimal(1 / count)
            else:
                allocation_user_fractions[uid]['fraction'] = Decimal(allocation_user_fractions[uid]['quantity']) / Decimal(total)

        logger.debug('Allocation user fractions %s', str(allocation_user_fractions))
        return allocation_user_fractions

    def createBillingRecordForUsage(self, product_usage, account, percent, year=None, month=None, description=None, usage_data=None):
        '''
        Run base class method then update BillingRecord description to combination of transaction descriptions
        '''
        if product_usage.product.product_name == 'Offer Letter Storage':
            raise Exception('Do not process offer letter storage until finalize()')
        billing_record = super().createBillingRecordForUsage(product_usage, account, percent, year, month, description, usage_data)
        # Join the transaction descriptions
        description = '\n'.join([trxn.description for trxn in billing_record.transaction_set.all()])
        billing_record.description = description
        billing_record.save()
        return billing_record

    def getOrganizationForProductUsage(self, product_usage):
        '''
        Get the organization from the allocation -> project -> project_organization
        '''
        return product_usage.organization

    def finalize(self, month, year, facility, recalculate=False, verbose=False):
        '''
        Create billing records for offer letter charges.

        The values accumulated for the offer letters are not persisted until this finalize method is run at the end.
        If there are any errors in this process, the entire month has to be rerun.
        '''
        for allocation_id, offer_letter_data in self.allocation_offer_letters.items():
            if 'offer_letter_charge' in offer_letter_data:
                try:
                    allocation = Allocation.objects.get(id=allocation_id)
                except Allocation.DoesNotExist:
                    raise Exception(f'Cannot find allocation for id {allocation_id} when processing offer letter data')

                logger.info('Processing offer_letter_charge for %s', str(allocation))

                product_organization = allocation.project.projectorganization_set.first()
                if not product_organization:
                    raise Exception(f'Unable to find an organization for the allocation {allocation} on project {allocation.project}')
                organization = product_organization.organization

                try:
                    # Multiple PI affiliations for Kovac lab
                    logger.info('Organization for allocation %s is %s', str(allocation), str(organization.name))
                    if organization.name == 'John Kovac Lab':
                        pi = get_user_model().objects.get(username='jmkovac')
                    else:
                        pi = organization.useraffiliation_set.get(role='pi').user
                except Exception as e:
                    raise Exception(f'Unable to find PI for {organization}: {e}')


                offer_letter_code = offer_letter_data.get('offer_letter_code')
                if not offer_letter_code:
                    raise Exception(f'Unable to find offer letter code for allocation {allocation}')
                try:
                    account = Account.objects.get(code=offer_letter_code)
                except Account.DoesNotExist:
                    raise Exception(f'Unable to find offer letter code {offer_letter_code}')

                offer_letter_tb = offer_letter_data.get('offer_letter_tb')
                if not offer_letter_tb:
                    raise Exception(f'Offer letter for allocation {allocation} has no TB amount')
                offer_letter_rate = offer_letter_data.get('rate')
                if not offer_letter_rate:
                    raise Exception(f'Offer letter for allcation {allocation} has no rate')

                year = offer_letter_data.get('year')
                month = offer_letter_data.get('month')
                if not year or not month:
                    raise Exception(f'Offer letter for allocation {allocation} needs both year and month')

                offer_letter_product = Product.objects.get(product_name='Offer Letter Storage')

                description = 'Offer letter subsidy'

                try:
                    offer_letter_usage = ProductUsage.objects.get(
                        product=offer_letter_product,
                        year=year,
                        month=month,
                        product_user=pi,
                        organization=organization,
                    )
                    if offer_letter_usage.billingrecord_set.count():
                        if recalculate:
                            offer_letter_usage.billingrecord_set.all().delete()
                        else:
                            raise Exception(f'Billing record exists for product usage {offer_letter_usage} and recalculate is not set.')
                except ProductUsage.DoesNotExist:
                    try:
                        offer_letter_usage = ProductUsage.objects.create(
                            product=offer_letter_product,
                            year=year,
                            month=month,
                            start_date=timezone.now(),
                            product_user=pi,
                            logged_by=pi,
                            organization=organization,
                            quantity=offer_letter_tb,
                            units='TB'
                        )
                    except Exception as e:
                        raise Exception(f'Unable to create Offer Letter Usage: {e}')

                charge = Decimal(offer_letter_rate.price) * int(offer_letter_tb)
                transactions_data = [
                    {
                        'charge': charge,
                        'description': description,
                        'author': pi,
                        'rate': self.getRateDescription(offer_letter_rate)
                    }
                ]
                logger.info('Setting up offer letter charge of %s against %s', str(charge), str(account))
                self.createBillingRecord(offer_letter_usage, account, year, month, transactions_data, 100, self.getRateDescription(offer_letter_rate), description)
