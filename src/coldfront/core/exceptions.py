# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


class JobFailed(Exception):
    """
    Raised within a ``JobRunner.run()`` to indicate that the job should be
    marked as failed (but not errored).

    Unlike an unexpected exception (which becomes ``ERRORED``), a ``JobFailed``
    exception indicates a controlled failure — e.g., a validation check that
    didn't pass. The job's status is set to ``FAILED`` rather than ``ERRORED``.
    """

    pass
