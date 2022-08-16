from django.conf import settings

from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import ResourceType


def get_compute_resource_names():
    """Returns sorted list of Resource names without ' Compute' in the name"""
    names = [x.replace(' Compute', '') for x in
             Resource.objects.filter(name__endswith=' Compute')
                 .values_list('name', flat=True).order_by('name')]
    return names


def get_computing_allowance_project_prefixes():
    """Return a tuple of prefixes (strs) that names of Projects with
    computing allowances should begin with."""
    resource_attribute_type = ResourceAttributeType.objects.get(name='code')
    resource_type = ResourceType.objects.get(name='Computing Allowance')
    resources = Resource.objects.filter(resource_type=resource_type)
    prefixes = ResourceAttribute.objects.filter(
        resource_attribute_type=resource_attribute_type,
        resource__in=resources).values_list(
            'value', flat=True)
    return tuple(prefixes)


def get_primary_compute_resource():
    """Return the 'Compute' Resource representing access to the primary
    cluster."""
    # TODO: All 'Compute' Resources should be updated so that the cluster's
    # TODO: name is capitalized.
    return Resource.objects.get(
        name__iexact=f'{settings.PRIMARY_CLUSTER_NAME} Compute')


def get_primary_compute_resource_name():
    """Return the name of the 'Compute' Resource representing access to
    the primary cluster."""
    return get_primary_compute_resource().name
