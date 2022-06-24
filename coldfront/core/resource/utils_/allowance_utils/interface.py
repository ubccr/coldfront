from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType


class ComputingAllowanceInterface(object):
    """A singleton that fetches computing allowances from the database
    and provides methods for retrieving associated data."""

    def __init__(self):
        """Retrieve database objects and instantiate data structures."""
        resource_type = ResourceType.objects.get(name='Computing Allowance')
        allowances = Resource.objects.prefetch_related(
            'resourceattribute_set').filter(resource_type=resource_type)

        # A mapping from name_short values to Resource objects.
        self._name_short_to_object = {}
        self.set_up_data_structures(allowances)

    def set_up_data_structures(self, allowances):
        """Fill in data structures."""
        for allowance in allowances:
            for attribute in allowance.resourceattribute_set.all():
                if attribute.resource_attribute_type.name == 'name_short':
                    self._name_short_to_object[attribute.value] = allowance

    def resource_from_name_short(self, name_short):
        """Given a name_short, return the corresponding Resource."""
        return self._name_short_to_object[name_short]
