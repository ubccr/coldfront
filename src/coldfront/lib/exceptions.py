# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.exceptions import ImproperlyConfigured


class PermissionsViolation(Exception):
    """
    Raised when an operation was prevented because it would violate the
    allowed permissions.
    """

    message = "Operation failed due to object-level permissions violation"


class AbortTransaction(Exception):
    """
    A dummy exception used to trigger a database transaction rollback.
    """

    pass


class AbortRequest(Exception):
    """
    Raised to cleanly abort a request (for example, by a pre_save signal receiver).
    """

    def __init__(self, message):
        self.message = message


class IncompatiblePluginError(ImproperlyConfigured):
    pass
