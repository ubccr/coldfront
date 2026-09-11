# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Small helpers shared by the task/job machinery.

These mirror utility functions from the ``django_tasks`` package that
ColdFront used previously; the task framework is now built on Django's
built-in ``django.tasks`` module, which does not ship a ``utils`` module.
"""

from traceback import format_exception

from django.utils.crypto import get_random_string

__all__ = (
    "get_exception_traceback",
    "get_module_path",
    "get_random_id",
)


def get_module_path(val) -> str:
    """Return the dotted import path (``module.qualname``) for a callable or class."""
    return f"{val.__module__}.{val.__qualname__}"


def get_exception_traceback(exc: BaseException) -> str:
    """Return the formatted traceback of an exception as a string."""
    return "".join(format_exception(exc))


def get_random_id() -> str:
    """
    Return a random string for use as a Task or worker id.

    Up to 64 characters is allowed; 32 is a sensible middle-ground.
    """
    return get_random_string(32)
