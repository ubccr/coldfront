from django.conf import settings

from coldfront.core.resource.models import Resource


def get_compute_resource_names():
    """Returns sorted list of Resource names without ' Compute' in the name"""
    names = [x.replace(' Compute', '') for x in
             Resource.objects.filter(name__endswith=' Compute')
                 .values_list('name', flat=True).order_by('name')]
    return names


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
