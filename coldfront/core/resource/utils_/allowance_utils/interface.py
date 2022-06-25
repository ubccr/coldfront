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

        # A mapping from allowance names to allowance Resource objects.
        self._name_to_object = {}
        # A mapping from name_short values to allowance Resource objects.
        self._name_short_to_object = {}
        # A mapping from allowance Resource objects to Service Units values.
        self._object_to_service_units = {}
        self.set_up_data_structures(allowances)

    def set_up_data_structures(self, allowances):
        """Fill in data structures."""
        for allowance in allowances:
            self._name_to_object[allowance.name] = allowance
            for attribute in allowance.resourceattribute_set.all():
                attribute_type_name = attribute.resource_attribute_type.name
                if attribute_type_name == 'name_short':
                    self._name_short_to_object[attribute.value] = allowance
                elif attribute_type_name == 'Service Units':
                    self._object_to_service_units[allowance] = attribute.value

    def allowance_from_name_short(self, name_short):
        """Given a name_short, return the corresponding allowance
        (Resource object)."""
        return self._name_short_to_object[name_short]

    def service_units_from_name(self, name):
        """Given a name, return the corresponding allowance's service
        units value."""
        return self._object_to_service_units[self._name_to_object[name]]
