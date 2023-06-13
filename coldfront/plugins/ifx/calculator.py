'''
Custom billing calculator class for Coldfront
'''
import logging
from collections import defaultdict
from decimal import Decimal
from django.core.exceptions import MultipleObjectsReturned
from django.db import connection, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from ifxbilling.calculator import BasicBillingCalculator, NewBillingCalculator
from ifxbilling.models import Account, Product, ProductUsage, Rate, BillingRecord
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.plugins.ifx import adjust
from .models import AllocationUserProductUsage


logger = logging.getLogger(__name__)

class NewColdfrontBillingCalculator(NewBillingCalculator):
    '''
    New one
    '''
    OFFER_LETTER_TB_ATTRIBUTE = 'Offer Letter'
    OFFER_LETTER_CODE_ATTRIBUTE = 'Offer Letter Code'
    STORAGE_QUOTA_ATTRIBUTE = 'Storage Quota (TB)'

    def generate_billing_records_for_organization(self, year, month, organization, recalculate, **kwargs):
        '''
        Create and save all of the :class:`~ifxbilling.models.BillingRecord` objects for the month for an organization.

        Finds the Project(s) for the Organization and then iterates over the Project Allocations

        If the Allocation has an Offer Letter and Offer Letter Code attribute, a corresponding billing record will be
        created and the total Allocation size reduced.

        Remaining Allocation will be distributed among the users proportional to their usage.

        Returns a dict that includes a list of successfully created :class:`~ifxbilling.models.BillingRecord` objects
        ("successes") and a list of error messages ("errors")

        :class:`~ifxbilling.models.BillingRecord` objects with a decimal_charge equivalent to Decimal('0.00') are
        not retained.

        If there are no users for an Allocation, the PI is set to the user

        :param year: Year that will be assigned to :class:`~ifxbilling.models.BillingRecord` objects
        :type year: int

        :param month: Month that will be assigned to :class:`~ifxbilling.models.BillingRecord` objects
        :type month: int

        :param organization: The organization whose :class:`~ifxbilling.models.BillingRecord` objects should be generated
        :type organization: list

        :param recalculate: If True, will delete existing :class:`~ifxbilling.models.BillingRecord` objects if possible
        :type recalculate: bool

        :return: A dictionary with keys "successes" (a list of successfully created :class:`~ifxbilling.models.BillingRecord` objects) and
            "errors" (a list of error messages)
        :rtype: dict
        '''
        successes = []
        errors = []

        projects = [po.project for po in organization.projectorganization_set.all()]
        if not projects:
            errors.append(f'No project found for {organization.name}')
        else:
            active = AllocationStatusChoice.objects.get(name='Active')
            for project in projects:
                for allocation in project.allocation_set.filter(status=active):
                    try:
                        allocation_tb = self.get_allocation_tb(allocation)
                        offer_letter_br, remaining_tb = self.process_offer_letter(year, month, organization, allocation, allocation_tb, recalculate)
                        if offer_letter_br:
                            successes.append(offer_letter_br)
                        if remaining_tb > Decimal('0'):
                            user_allocation_percentages = self.get_user_allocation_percentages(year, month, allocation)
                            for user_id, allocation_percentage_data in user_allocation_percentages.items():
                                try:
                                    user = get_user_model().objects.get(id=user_id)
                                except get_user_model().DoesNotExist:
                                    raise Exception(f'Cannot find user with id {user_id}')
                                brs = self.generate_billing_records_for_allocation_user(
                                    year,
                                    month,
                                    user,
                                    organization,
                                    allocation,
                                    allocation_percentage_data['fraction'],
                                    allocation_tb,
                                    recalculate,
                                    remaining_tb,
                                )
                                if brs:
                                    successes.extend(brs)
                    except Exception as e:
                        errors.append(str(e))
                        if self.verbosity == self.CHATTY:
                            logger.error(e)
                        if self.verbosity == self.LOUD:
                            logger.exception(e)

        return (successes, errors)

    def process_offer_letter(self, year, month, organization, allocation, allocation_tb, recalculate):
        '''
        Generate a ProductUsage and a BillingRecord for the offer letter, if it exists.
        Return BillingRecord (may be None) and remaining allocation size (Decimal TB).  If
        no BillingRecord is generated, the remaining size is the full allocation size.
        '''
        offer_letter_br = None
        offer_letter_product = self.get_offer_letter_product(allocation)

        # Decimal quantity in TB
        offer_letter_tb = self.get_offer_letter_tb(allocation)

        # Account for offer letter code
        offer_letter_acct = self.get_offer_letter_account(allocation, organization)

        remaining_tb = allocation_tb

        if offer_letter_tb:
            if not offer_letter_acct:
                raise Exception(f'Project {allocation.project.title} allocation {allocation.get_resources_as_string()} has an offer letter, but no code.')

            # Offer letter product user (the PI)
            product_user = self.get_offer_letter_product_user(allocation)

            # Does the billing record exist?  If so and recalculate is true, delete it and product usage.  Otherwise, exception
            try:
                old_br = BillingRecord.objects.get(
                    product_usage__product=offer_letter_product,
                    year=year,
                    month=month,
                    product_usage__organization=organization,
                    account=offer_letter_acct,
                )
                if recalculate:
                    old_pu = old_br.product_usage
                    old_pu.billingrecord_set.all().delete()
                    old_pu.delete()
                else:
                    raise Exception(f'Offer letter billing record exists for {year}-{month} product {offer_letter_product} and organization {organization}')
            except BillingRecord.DoesNotExist:
                pass


            # Create the offer letter product usage.
            try:
                offer_letter_usage = ProductUsage.objects.create(
                    product=offer_letter_product,
                    year=year,
                    month=month,
                    start_date=timezone.now(),
                    product_user=product_user,
                    logged_by=product_user,
                    organization=organization,
                    quantity=offer_letter_tb,
                    decimal_quantity=offer_letter_tb,
                    units='TB'
                )
            except Exception as e:
                raise Exception(f'Unable to create Offer Letter Usage: {e}') from e

            # Get the allocation resource product rate for calculating charges
            storage_product_rate = self.get_allocation_resource_product_rate(allocation)
            if not storage_product_rate.units == 'TB':
                raise Exception(f'Storage product rates should be in TB.  Rate {storage_product_rate.name} is in {storage_product_rate.units}')
            decimal_price = storage_product_rate.decimal_price
            if not decimal_price:
                raise Exception(f'decimal_price for {storage_product_rate.product.product_name} is not set.')
            charge = decimal_price * offer_letter_tb

            # Transaction and rate description
            rate_desc = self.get_rate_description(storage_product_rate)
            description = f'Faculty commitment of ${charge.quantize(settings.TWO_DIGIT_QUANTIZE)} for {offer_letter_tb} TB of {offer_letter_product.product_name} at ${rate_desc}'

            transactions_data = [
                {
                    'charge': charge,
                    'decimal_charge': charge,
                    'description': description,
                    'author': product_user,
                    'rate': rate_desc,
                }
            ]
            billing_data_dict = {}
            if self.verbosity > 0:
                logger.info('Setting up offer letter charge of %s against %s', str(charge), str(offer_letter_acct))
            offer_letter_br = self.create_billing_record(
                year,
                month,
                offer_letter_usage,
                offer_letter_acct,
                100,
                storage_product_rate,
                offer_letter_tb,
                transactions_data,
                billing_data_dict
            )

            remaining_tb = allocation_tb - offer_letter_tb

        return offer_letter_br, remaining_tb

    def get_offer_letter_product(self, allocation):
        '''
        Return the Product associated with Offer Letters

        :param allocation:  The Allocation
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :return: Product for Offer Letters
        :rtype: `~ifxbilling.models.Product`
        '''
        resources = allocation.resources.all()
        if not resources:
            raise Exception(f'Allocation {allocation} has no resources')
        if len(resources) > 1:
            raise Exception(f'Allocation {allocation} has more than one resource')
        resource = resources[0]
        product_resources = resource.productresource_set.all()
        if not product_resources:
            raise Exception(f'Resource {resource} has no product')
        if len(product_resources) > 1:
            raise Exception(f'Resource {resource} has multiple products')

        return product_resources[0].product

    def get_offer_letter_product_user(self, allocation):
        '''
        Return product_user for offer letter billing record (the PI) for a given allocation

        :param allocation: The Allocation
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :raises: Exception if PI is missing
        :return: The PI user
        :rtype: `~ifxuser.models.IfxUser`
        '''
        pi = allocation.project.pi
        if not pi:
            raise Exception(f'Allocation of {allocation.get_resources_as_string()} for {allocation.project.title} has no PI')
        return pi

    def get_offer_letter_tb(self, allocation):
        '''
        Returns the relevant offer letter size as a Decimal or None if nothing is found

        :param allocation: The `~coldfront.core.allocation.models.Allocation`
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :return: Decimal representing the offer letter in TB or None
        :rtype: `~decimal.Decimal` or NoneType
        '''
        offer_letter_tb = allocation.get_attribute(self.OFFER_LETTER_TB_ATTRIBUTE)
        if offer_letter_tb:
            offer_letter_tb = Decimal(offer_letter_tb)
        return offer_letter_tb

    def get_offer_letter_account(self, allocation, organization):
        '''
        Returns the relevant offer letter expense code or None if nothing is found

        :param allocation: The `~coldfront.core.allocation.models.Allocation`
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :return: Account corresponding to the offer letter expense code or None
        :rtype: `~ifxbilling.models.Account` or NoneType
        '''
        code = allocation.get_attribute(self.OFFER_LETTER_CODE_ATTRIBUTE)
        if code:
            try:
                code = Account.objects.get(code=code, organization=organization)
            except Account.DoesNotExist:
                raise Exception(f'Cannot find offer letter code {code}')
        return code

    def get_allocation_tb(self, allocation):
        '''
        Return the size of the allocation in TB.  Return value is a Python Decimal.

        :param allocation: The Allocation
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :return: Size of the allocation as a Decimal
        :rtype: `~decimal.Decimal`
        '''
        allocation_size_tb = allocation.get_attribute(self.STORAGE_QUOTA_ATTRIBUTE)
        if not allocation_size_tb:
            raise Exception(f'Allocation {allocation.id} ({allocation.get_resources_as_string()} for {allocation.project.title}) does not have the {self.STORAGE_QUOTA_ATTRIBUTE} attribute')
        return Decimal(allocation_size_tb)

    def get_allocation_resource_product(self, allocation):
        '''
        Return the product association with the allocation resource

        :param allocation: The Allocation
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :raises: Exception if there is not exactly one Resource for the Allocation or exactly one
            Product for the Resource

        :return: The Allocation storage Product
        :rtype: `~ifxbilling.models.Product`
        '''
        resources = allocation.resources.all()
        if not resources:
            raise Exception(f'Allocation {allocation.id} has no resources')
        if len(resources) > 1:
            raise Exception(f'Allocation {allocation.id} has more than one resource. Cannot figure out a Product Rate.')

        products = [pr.product for pr in resources[0].productresource_set.all()]
        if not products:
            raise Exception(f'Allocation {allocation.id} resource {resources[0]} has no associated Product.')
        if len(products) > 1:
            raise Exception(f'Allocation {allocation.id} resource {resources[0]} has multiple Products.')

        return products[0]

    def get_allocation_resource_product_rate(self, allocation):
        '''
        Get the active Rate for the Product associated with the Allocation's Resource

        :param allocation: The Allocation
        :type allocation: `~coldfront.core.allocation.models.Allocation`

        :raises: Exception if there is not exactly one active Rate for the Product

        :return: Active rate for the storage product
        :rtype: `~ifxbilling.models.Rate`
        '''
        product = self.get_allocation_resource_product(allocation)
        try:
            rate = product.rate_set.get(is_active=True)
        except Rate.DoesNotExist:
            raise Exception(f'Cannot find an active rate for Product {product.product_name}')

        return rate

    def get_rate_description(self, rate, **kwargs):
        '''
        Text description of rate for use in txn rate and description.
        Empty string is returned if rate.price or rate.units is None.

        Description is <price> per <units>

        :param rate: The :class:`~ifxbilling.models.Rate` for the :class:`~ifxbilling.models.Product`
            from the :class:`~ifxbilling.models.ProductUsage`
        :type rate: :class:`~ifxbilling.models.Rate`

        :return: Text description of the rate
        :rtype: str
        '''
        desc = ''
        if rate.decimal_price is not None and rate.units is not None:
            desc = f'{rate.decimal_price.quantize(Decimal("0.00"))} per {rate.units}'
        return desc

    def get_user_allocation_percentages(self, year, month, allocation):
        '''
        Return a dictionary of user and their percentage of the total allocation
        '''
        # Of the form
        # allocation_user_fractions = {
        #    <allocation user id 1>: {
        #       'fraction': 0.2,
        #       'quantity': 2000
        #    }
        #    <allocation user id 2>: {
        #        'fraction': 0.8,
        #        'quantity': 8000
        #    }
        # }

        allocation_user_fractions = {}
        product = self.get_allocation_resource_product(allocation)

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
                            and acct.valid_from <= pu.start_date
                            and acct.expiration_date > pu.start_date
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
                            and acct.valid_from <= pu.start_date
                            and acct.expiration_date > pu.start_date
                            and ua.product_id = %s
                    )
                group by pu.product_user_id
            ) t
            group by product_user_id
        '''.replace('\n', ' ')

        cursor = connection.cursor()
        cursor.execute(sql, [allocation.id, year, month, allocation.id, year, month, product.id])
        total = 0
        count = 0
        for row in cursor.fetchall():
            if row[1] is None:
                raise Exception(f'ProductUsage quantity is None for allocation {allocation}')
            if row[1] > Decimal('0'):
                allocation_user_fractions[row[0]] = {
                    'quantity': row[1]
                }
                total += row[1]
                count += 1

        if total == 0 and count == 0:
            # If there are no users, set count to 1 and add PI user id
            pi = allocation.project.pi
            allocation_user_fractions[pi.id] = {
                'quantity': 1,
                'fraction': 1,
            }
            if self.verbosity > 0:
                logger.info(f'Allocation {allocation} has no users at all. Setting PI {pi} as user.')

        for uid in allocation_user_fractions.keys():
            # For the situation where there is an allocation, and the PI is an allocation user, but no data is used
            # set fraction to 1.
            if total == 0:
                if count > 1:
                    logger.error(f'Allocation {allocation} from {allocation.project} has {count} 0 byte users')
                allocation_user_fractions[uid]['fraction'] = Decimal(1)
            else:
                allocation_user_fractions[uid]['fraction'] = Decimal(allocation_user_fractions[uid]['quantity']) / Decimal(total)
        return allocation_user_fractions

    def get_billing_data_dicts_for_usage(self, product_usage, **kwargs):
        '''
        Return a list of dictionaries containing the data needed to create a billing record from the usage
        Each dict should be enough for a single billing record.

        This class returns a dict of 'rate_obj', 'decimal_quantity', 'account' and 'percent' corresponding
        to any splits along with the active rate.  allocation_percentage and allocation_tb
        are passed through from the kwargs.  remaining_tb in kwargs is used as the decimal_quantity

        :param product_usage: The :class:`~ifxbilling.models.ProductUsage` associated with the instance
        :type product_usage: :class:`~ifxbilling.models.ProductUsage`

        :param kwargs: Should include allocation_percentage, allocation_tb, and remaining_tb (may be None)
        :type kwargs: dict

        :return: A list of dictionaries
        :rtype: list
        '''
        billing_data_dicts = []
        allocation_percentage = kwargs.get('allocation_percentage')
        allocation_tb = kwargs.get('allocation_tb')
        if allocation_percentage is None:
            raise Exception(f'Allocation percentage not set for usage {product_usage}')
        if not allocation_tb:
            raise Exception(f'Allocation TB not set for {product_usage}')

        # If remaining tb is not set (there is no offer letter), default to allocation_tb
        decimal_quantity = kwargs.get('remaining_tb', allocation_tb)

        rate_obj = self.get_rate(product_usage=product_usage, name=settings.RATES.INTERNAL_RATE_NAME)
        account_percentages = self.get_account_percentages_for_product_usage(product_usage)

        for account_percent in account_percentages:
            billing_data_dicts.append(
                {
                    'decimal_quantity': decimal_quantity,
                    'rate_obj': rate_obj,
                    'account': account_percent['account'],
                    'percent': account_percent['percent'],
                    'allocation_percentage': allocation_percentage,
                    'allocation_tb': allocation_tb,
                }
            )

        return billing_data_dicts

    def generate_billing_records_for_allocation_user(self, year, month, user, organization, allocation, allocation_percentage, allocation_tb, recalculate=False, remaining_tb=None):
        '''
        Make the BillingRecords for the given user from their allocation percentage and the allocation size.

        Gets ProductUsage from Allocation and User
        Checks for existing BillingRecord, using recalculate to decide to delete
        Sets the decimal_quantity in ProductUsage to the calculated usage (percentage of allocation after offer letter)
        Calls `~ifxbilling.calculator.NewBillingCalculator.generate_billing_records_for_usage` daadaad
        '''
        product_usage = self.get_product_usage_for_allocation_user(year, month, user, organization, allocation)

        if BillingRecord.objects.filter(product_usage=product_usage).exists():
            if recalculate:
                BillingRecord.objects.filter(product_usage=product_usage).delete()
            else:
                msg = f'Billing record already exists for usage {product_usage}'
                raise Exception(msg)

        # Set the decimal_quantity to TB percentage of allocation
        product_usage = self.set_product_usage_decimal_quantity(product_usage, allocation_percentage, allocation_tb)
        brs = self.generate_billing_records_for_usage(year, month, product_usage, allocation_percentage=allocation_percentage, allocation_tb=allocation_tb, remaining_tb=remaining_tb)

        # Remove zero dollar billing records
        result = []
        for br in brs:
            if not self.billing_record_is_zero_charge(br):
                result.append(br)
            else:
                br.delete()
                if self.verbosity > 0:
                    logger.info(f'Charge for {product_usage} was essentially zero and therefore discarded.')
        return result

    def billing_record_is_zero_charge(self, billing_record):
        '''
        Billing record is zero charge if transactions are all zero
        '''
        zero_dollars = Decimal('0.00')
        return all([txn.decimal_charge.quantize(zero_dollars) == zero_dollars for txn in billing_record.transaction_set.all()])

    def calculate_charges(self, product_usage, percent, rate_obj, decimal_quantity, billing_data_dict):
        '''
        Check for the Allocation information in the usage_data dictionary.  If it's there, use the
        fractions to figure out the charge.  If not, get the other AllocationUser data to calculate
        the fractions and save in the usage_data dict.
        '''

        rate_desc = self.get_rate_description(rate_obj)

        transactions_data = []

        percent_str = ''
        if percent < 100:
            percent_str = f'a {percent}% split of '

        user = product_usage.product_user
        allocation_tb = billing_data_dict.get('allocation_tb')
        if allocation_tb is None:
            raise Exception(f'Allocation TB was not set for {product_usage}')

        # Remaining TB after offer letter.  If no offer letter, should be the same as allocation_tb.
        # In case it isn't set (it should be), use allocation_tb
        remaining_tb = decimal_quantity

        # Decimal charge rounded to 4 decimal places
        allocation_fraction = billing_data_dict.get('allocation_percentage')
        allocation_tb = billing_data_dict.get('allocation_tb')
        if allocation_fraction is None or not allocation_tb:
            raise Exception(f'Allocation percentage {allocation_fraction} / Allocation TB {allocation_tb} not passed to calculate_charges')

        decimal_charge = Decimal(rate_obj.decimal_price * allocation_fraction * remaining_tb * Decimal(percent / 100)).quantize(settings.STANDARD_QUANTIZE)

        # Round to dollars
        decimal_charge_str = self.get_decimal_charge_str(decimal_charge)
        price_str = self.get_decimal_charge_str(rate_obj.decimal_price)

        # If there is an offer letter, then need to add to description
        remaining_space_str = ''
        if allocation_tb != remaining_tb:
            offer_letter_tb = allocation_tb - remaining_tb
            remaining_space_str = f' remaining after faculty commitment of {offer_letter_tb} TB'
        allocation_percent = Decimal(allocation_fraction * 100).quantize(Decimal('0.01'))
        allocation_string = f'{allocation_percent}% of {remaining_tb} TB of {product_usage.product.product_name}{remaining_space_str}'

        description = f'{decimal_charge_str} for {percent_str}{allocation_string} at {price_str} per TB'

        transactions_data.append(
            {
                'charge': round(decimal_charge),
                'decimal_charge': decimal_charge,
                'description': description,
                'author': user,
                'rate': rate_desc,
            }
        )
        return transactions_data

    def set_product_usage_decimal_quantity(self, product_usage, allocation_percentage, allocation_tb):
        '''
        Set decimal_quantity to the percentage of the remaining allocation quantity in TB
        '''
        product_usage.decimal_quantity = Decimal(allocation_percentage * allocation_tb).quantize(settings.STANDARD_QUANTIZE)
        product_usage.units = 'TB'
        product_usage.save()
        return product_usage

    def get_product_usage_for_allocation_user(self, year, month, user, organization, allocation):
        '''
        For the given params, get the ProductUsage from the Allocation
        '''
        try:
            aupu = AllocationUserProductUsage.objects.get(
                allocation_user__allocation=allocation,
                product_usage__product_user=user,
                product_usage__year=year,
                product_usage__month=month,
                product_usage__organization=organization,
            )
        except AllocationUserProductUsage.DoesNotExist:
            raise Exception(f'No AllocationUserProductUsage was found for allocation {allocation} and user {user} with organization {organization}')
        except MultipleObjectsReturned:
            raise Exception(f'More than one AllocationUserProductUsage found for allocation {allocation}, user {user} with organization {organization}')

        return aupu.product_usage

    def calculate_billing_month(self, year, month, organizations=None, recalculate=False, verbosity=0):
        '''
        Adjust march 2023 due to bad DR issues
        '''
        results = super().calculate_billing_month(year, month, organizations, recalculate, verbosity)
        if year == 2023 and (month == 3 or month == 4):
            adjust.march_april_2023_dr()

        return results



class Resultinator():
    '''
    Makes billing calculator results easier to work with
    '''

    def __init__(self, results):
        '''
        init
        '''
        self.results = results
        self.error_types = {
            ''
        }

    def get_errors_by_organization(self, organization_name=None):
        '''
        Return dict of all of the non "No project" errors keyed by lab
        If organization is set, just get those
        '''
        errors_by_lab = {}
        for lab, output in self.results.items():
            if output[1] and 'No project' not in output[1][0]:
                if organization_name is None or lab == organization_name:
                    errors_by_lab[lab] = output[1]
        return errors_by_lab

    def get_successes_by_organization(self, organization_name=None):
        '''
        Return dict of successes keyed by lab
        '''
        successes_by_lab = {}
        for lab, output in self.results.items():
            if output[0]:
                if organization_name is None or lab == organization_name:
                    successes_by_lab[lab] = output[0]
        return successes_by_lab

    def get_organizations_by_error_type(self):
        '''
        Returns a dictionary keyed by error type and listing the organization names with that issue.
        Errors that don't match are used as individual keys
        '''
        pass

