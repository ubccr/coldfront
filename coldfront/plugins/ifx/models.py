'''
Models for ifxbilling plugin
'''
import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from coldfront.core.allocation.models import AllocationUser, AllocationAttribute
from coldfront.core.resource.models import Resource
from ifxbilling.models import ProductUsage, Product
from ifxbilling.fiine import createNewProduct
from fiine.client import API as FiineAPI

logger = logging.getLogger(__name__)


class AllocationUserProductUsage(models.Model):
    '''
    Link between ProductUsage and Allocation
    '''
    allocation_user = models.ForeignKey(
        AllocationUser.history.model,
        on_delete=models.PROTECT
    )
    product_usage = models.ForeignKey(
        ProductUsage,
        on_delete=models.CASCADE
    )

class ProductResource(models.Model):
    '''
    Link between Resources and Products
    '''
    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

def allocation_user_to_allocation_product_usage(allocation_user, product, overwrite=False):
    '''
    Converts an allocation_user to an allocation_product_usage.
    Unless overwrite flag is true, throws an exception if there is already an
    allocation_product_usage for this allocation user, year, and month.  Otherwise, removes existing AllocationUserProductUsage
    and ProductUsage records before creating new ones.
    '''
    product_user = allocation_user.user
    month = allocation_user.modified.strftime('%m')
    year = allocation_user.modified.year
    aupus = AllocationUserProductUsage.objects.filter(
        product_usage__product=product,
        product_usage__product_user=product_user,
        product_usage__month=month,
        product_usage__year=year
    )
    if len(aupus) > 0:
        if overwrite:
            for aupu in aupus:
                aupu.product_usage.delete()
                aupu.delete()
        else:
            raise Exception(f'AllocationUserProductUsage already exists for use of {product} by {product_user} in month {month} of {year}')

    product_usage_data = {
        'product': product,
        'product_user': product_user,
        'month': month,
        'year': year,
    }
    product_usage_data['quantity'] = allocation_user.usage_bytes / 1024**4
    product_usage_data['units'] = 'T'
    product_usage, created = ProductUsage.objects.get_or_create(**product_usage_data)
    aupu = AllocationUserProductUsage.objects.create(allocation_user=allocation_user.history.first(), product_usage=product_usage)
    return aupu

@receiver(post_save, sender=Resource)
def resource_post_save(sender, instance, **kwargs):
    '''
    Ensure that there is a Product for each Resource
    '''
    try:
        product_resource = ProductResource.objects.get(resource=instance)
    except ProductResource.DoesNotExist:
        # Need to create a Product and ProductResource for this Resource
        products = FiineAPI.listProducts(product_name=instance.name)
        if not products:
            product = createNewProduct(product_name=instance.name, product_description=instance.name)
        else:
            fiine_product = products[0].to_dict()
            fiine_product.pop('facility')
            (product, created) = Product.objects.get_or_create(**fiine_product)
        product_resource = ProductResource.objects.create(product=product, resource=instance)

class SuUser(get_user_model()):
    '''
    This is just so that we can have an admin interface with su
    '''
    class Meta:
        proxy = True