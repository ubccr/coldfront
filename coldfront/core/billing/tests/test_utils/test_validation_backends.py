from coldfront.core.billing.tests.test_billing_base import TestBillingBase
from coldfront.core.billing.utils.validation.backends.dummy import DummyValidatorBackend
from coldfront.core.billing.utils.validation.backends.permissive import PermissiveValidatorBackend


class TestValidatorBackendBase(TestBillingBase):
    """A base class for testing billing validator backends."""

    def setUp(self):
        """Set up test data."""
        pass

    def assert_valid(self, validator, billing_id, negate=False):
        """Assert that the given billing ID is valid, according to the
        given validator. If negate is True, assert that it is
        invalid."""
        func = self.assertTrue if not negate else self.assertFalse
        func(validator.is_billing_id_valid(billing_id))


class TestDummyValidatorBackend(TestValidatorBackendBase):
    """A class for testing the DummyValidatorBackend class."""

    def setUp(self):
        """Set up test data."""
        self.validator = DummyValidatorBackend()

    def test_evens_valid(self):
        """Test that the validator treats billing IDs whose last digit
        is even as valid."""
        for billing_id in ('123456-788', '123456-790', '123456-792'):
            self.assert_valid(self.validator, billing_id)

    def test_odds_invalid(self):
        """Test that the validator treats billing IDs whose last digit
        is odd as invalid."""
        for billing_id in ('123456-789', '123456-791', '123456-793'):
            self.assert_valid(self.validator, billing_id, negate=True)


class TestPermissiveValidatorBackend(TestValidatorBackendBase):
    """A class for testing the PermissiveValidatorBackend class."""

    def setUp(self):
        """Set up test data."""
        self.validator = PermissiveValidatorBackend()

    def test_all_valid(self):
        """Test that the validator treats all billing IDs as valid."""
        billing_ids = (
            '123456-788',
            '123456-789',
            '123456-790',
            '123456-791',
            '123456-792',
            '123456-793',
        )
        for billing_id in billing_ids:
            self.assert_valid(self.validator, billing_id)


class TestOracleValidatorBackend(TestValidatorBackendBase):
    """A class for testing the OracleValidatorBackend class."""

    # TODO
    # Note: The backend is not generally accessible, and validity for a
    # particular billing ID may change over time.
    pass
