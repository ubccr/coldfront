'''
Models for ifxbilling plugin
'''
import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from coldfront.core.allocation.models import Allocation, AllocationAttribute
from coldfront.core.resource.models import Resource
from ifxbilling.models import ProductUsage, Product
from ifxbilling.fiine import createNewProduct
from fiine.client import API as FiineAPI

logger = logging.getLogger(__name__)


class AllocationProductUsage(models.Model):
    '''
    Link between ProductUsage and Allocation
    '''
    allocation = models.ForeignKey(
        Allocation,
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

def allocation_to_product_usage(allocation, product):
    '''
    Converts an allocation to a product usage.
    Temporarily using PI as the product_user.  Returns existing
    product usage if found.
    '''
    product_usage_data = {
        'product': product,
    }
    product_user = get_user_model().objects.get(username='veradmin')
    if allocation.project.pi:
        product_user = allocation.project.pi
    product_usage_data['product_user'] = product_user
    storage_quota = allocation.get_attribute('Storage Quota (TB)')
    product_usage_data['quantity'] = int(float(storage_quota))
    product_usage_data['units'] = 'TB'
    product_usage_data['year'] = allocation.start_date.year
    product_usage_data['month'] = allocation.start_date.strftime("%m")
    product_usage, created = ProductUsage.objects.get_or_create(**product_usage_data)
    return product_usage

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


@receiver(post_save, sender=AllocationAttribute)
def allocation_post_save(sender, instance, **kwargs):
    '''
    Fill out AllocationProductUsage and ProductUsage records when AllocationAttribute changes
    Need to figure out if existing records must be removed.  Need to figure
    out if multiple AllocationProductUsages will exist for an allocation- probably yes.
    '''
    if instance.allocation_attribute_type.name == 'Storage Quota (TB)':
        allocation = instance.allocation
        try:
            allocation_product_usage = AllocationProductUsage.objects.get(allocation=allocation)
        except AllocationProductUsage.DoesNotExist:
            resources = allocation.resources.all()
            for resource in resources:
                product_resource = ProductResource.objects.get(resource=resource)
                product_usage = allocation_to_product_usage(allocation, product_resource.product)
                allocation_product_usage, created = AllocationProductUsage.objects.get_or_create(
                    allocation=allocation,
                    product_usage=product_usage
                )