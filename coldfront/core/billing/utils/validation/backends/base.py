from abc import ABC
from abc import abstractmethod


class BaseValidatorBackend(ABC):
    """An interface for checking whether billing IDs are valid using any
    of a number of backends."""

    @abstractmethod
    def is_billing_id_valid(self, billing_id):
        """Return whether the given billing ID is valid."""
        pass
