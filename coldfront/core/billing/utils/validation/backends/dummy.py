from coldfront.core.billing.utils.validation.backends.base import BaseValidatorBackend


class DummyValidatorBackend(BaseValidatorBackend):
    """A backend for testing purposes."""

    def is_billing_id_valid(self, billing_id):
        """Return whether the last digit of the given billing ID is
        even."""
        return int(billing_id[-1]) % 2 == 0
