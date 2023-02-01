from coldfront.core.billing.utils.validation.backends.base import BaseValidatorBackend


class PermissiveValidatorBackend(BaseValidatorBackend):
    """A backend that treats all billing IDs as valid."""

    def is_billing_id_valid(self, billing_id):
        """Return True."""
        return True
