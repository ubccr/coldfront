# -*- coding: utf-8 -*-

'''
Code for ad hoc billing adjustments

Created on  2023-04-10

@author: Aaron Kitzmiller <akitzmiller@g.harvard.edu>
@copyright: 2023 The Presidents and Fellows of Harvard College.
All rights reserved.
@license: GPL v2.0
'''

import logging
from django.db import transaction
from django.db.models import Q
from ifxbilling.models import ProductUsage, ProductUsageProcessing

logger = logging.getLogger(__name__)

def march_april_2023_dr():
    '''
    Remove all charges for bos-isilon/tier1 and holy-isilon/tier1 storage due to disaster recovery failure
    Set PUP message
    '''

    year = 2023
    products = ['holy-isilon/tier1', 'bos-isilon/tier1']
    count = 0
    billing_record_count = 0
    for pu in ProductUsage.objects.filter(year=year, product__product_name__in=products).filter(Q(month=3) | Q(month=4)):
        with transaction.atomic():
            pup = pu.productusageprocessing_set.first()
            if not pup:
                pup = ProductUsageProcessing(product_usage=pu)
            pup.error_message = f'Billing Record removed for March / April 2023 due to tier1 disaster recovery issues'
            pup.resolved = True
            pup.save()
            delete_result = pu.billingrecord_set.all().delete()
            count += 1
            if delete_result and 'ifxbilling.BillingRecord' in delete_result[1]:
                billing_record_count += delete_result[1]['ifxbilling.BillingRecord']

    logger.info(f'Removed {billing_record_count} billing records from {count} usages of {", ".join(products)}')
