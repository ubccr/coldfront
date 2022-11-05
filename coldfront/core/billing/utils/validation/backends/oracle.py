from django.conf import settings

from lbl_project_activity_validator.backends import OracleBackend
from lbl_project_activity_validator.project_activity import ProjectActivity
from lbl_project_activity_validator.validator import ProjectActivityValidator

from coldfront.core.billing.utils.validation.backends.base import BaseValidatorBackend


"""This module should only be imported if lbl_project_activity_validator
is installed."""


class OracleValidatorBackend(BaseValidatorBackend):
    """A backend that invokes a Python package which connects to an
    Oracle database to validate billing IDs."""

    def __init__(self):
        db_settings = settings.ORACLE_BILLING_DB
        backend = OracleBackend(
            db_settings['user'], db_settings['password'], db_settings['dsn'])
        self._validator = ProjectActivityValidator(backend)

    def is_billing_id_valid(self, billing_id):
        """Return the output of the underlying validation method."""
        project_activity = ProjectActivity(billing_id)
        return self._validator.is_project_activity_valid(project_activity)
