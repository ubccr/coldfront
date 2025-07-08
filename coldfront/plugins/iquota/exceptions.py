# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


class IquotaError(Exception):
    """Base error class."""

    def __init__(self, message):
        self.message = message


class KerberosError(IquotaError):
    """Kerberos Auth error"""

    pass


class MissingQuotaError(IquotaError):
    """User request error"""

    pass
