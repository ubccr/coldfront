from flags.state import flag_enabled

from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances


class ComputingAllowance(object):
    """A wrapper class around a Resource representing a computing
    allowance, with helper methods."""

    def __init__(self, resource):
        assert isinstance(resource, Resource)
        self._resource = resource
        self._name = self._resource.name

    def is_one_per_pi(self):
        """Return whether a PI may have at most one of the allowance."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.ICA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def is_periodic(self):
        """Return whether the allowance is limited to a specific
        AllocationPeriod."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.ICA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names
