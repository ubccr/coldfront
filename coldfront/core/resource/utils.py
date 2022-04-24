from coldfront.core.resource.models import Resource


def get_compute_resource_names():
    """Returns sorted list of Resource names without ' Compute' in the name"""
    names = [x.replace(' Compute', '') for x in
             Resource.objects.filter(name__icontains='Compute')
                 .values_list('name', flat=True).order_by('name')]
    return names
