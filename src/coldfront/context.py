# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from contextvars import ContextVar

__all__ = (
    "current_request",
    "query_cache",
    "signals_received",
)


current_request = ContextVar("current_request", default=None)
query_cache = ContextVar("query_cache", default=None)

# Used to track received signals per object
signals_received = ContextVar("signals_received", default=None)
