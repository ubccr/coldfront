# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm REST API exception hierarchy.

All Slurm REST API errors inherit from :class:`SlurmError`.
Callers can catch the base exception to handle any Slurm API failure,
or catch specific subclasses to react to particular error conditions.

The hierarchy maps only error codes that the **supported slurmrestd
versions actually emit** (verified live against the e2e stack). Error
codes that never occur on the supported versions are deliberately not
mapped — e.g. the REST layer surfaces auth failures (403) and missing
entities (404) as 502/503 unavailability and silent success on this
stack, so ``SlurmAuthError``/``SlurmNotFoundError``/conflict classes
do not exist.

Mapped live behaviors:
- 422 / 400 malformed payload -> :class:`SlurmBadRequestError`
- 502 / 503 / 504 transient or unreachable -> :class:`SlurmUnavailableError`
- HTTP 200 with a silent no-op (nothing stored) -> the
  :class:`SlurmNotCreatedError` verification classes
"""


class SlurmError(Exception):
    """Base exception for all Slurm REST API failures.

    Every exception raised by :class:`SlurmClient` inherits from this
    class, allowing callers to catch a single base type for generic
    error handling (e.g., logging, retry logic).

    Attributes:
        message: Human-readable description of the failure.
        errors: List of error detail strings returned by the API.
        warnings: List of warning strings returned by the API.
        status_code: HTTP status code from the response (if applicable).
    """

    def __init__(
        self,
        message: str = "Slurm REST API failed",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message
        self.errors = errors or []
        self.warnings = warnings or []
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.errors:
            parts.append(f"errors={self.errors}")
        if self.status_code:
            parts.append(f"status={self.status_code}")
        return " | ".join(parts)


class SlurmBadRequestError(SlurmError):
    """Malformed request body or invalid query parameters.

    Raised when the API rejects the payload as invalid (400 Bad Request
    / 422 Unprocessable Entity). Live-verified: an account missing
    ``description``/``organization`` returns 422 and raises this type.

    Maps to ``ESLURM_REST_INVALID_QUERY``, ``ESLURM_REST_FAIL_PARSING``,
    ``ESLURM_REST_INVALID_JOBS_DESC``, ``ESLURM_HTTP_INVALID_CONTENT_LENGTH``.
    """

    def __init__(
        self,
        message: str = "Slurm bad request",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 400,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmUnavailableError(SlurmError):
    """Service unavailable or transient failure.

    Raised when ``slurmrestd`` cannot reach ``slurmdbd`` or the
    Slurm controller, or when a communication error occurs
    (503 Service Unavailable / 502 Bad Gateway).

    These are typically transient and should be retried with
    exponential backoff.

    Live-verified: an invalid JWT surfaces as 502/503 (unavailability),
    not an auth error, so this is the only type raised on bad credentials.

    Maps to ``ESLURM_DB_CONNECTION``, ``SLURM_COMMUNICATIONS_CONNECTION_ERROR``,
    ``SLURMCTLD_COMMUNICATIONS_BACKOFF``.
    """

    def __init__(
        self,
        message: str = "Slurm service unavailable",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 503,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmNotCreatedError(SlurmError):
    """An entity was requested but did not materialize in Slurm accounting.

    Raised when a create operation returns success (HTTP 200, no errors) but
    the entity does not appear in a follow-up read-back. This catches
    slurmdbd's **silent no-ops** — e.g. a user with no uid in /etc/passwd, an
    association whose parent account association does not exist, or a user
    whose default account is missing — where the REST layer returns a clean
    response but stores nothing.

    Subclasses carry ``missing`` (the entities that failed to materialize) so
    callers can report precisely which writes were dropped. Unlike the HTTP-
    mapped exceptions, this is not an HTTP error: the request itself returned
    200, so ``status_code`` is ``None``.

    Attributes:
        missing: List of the requested entities that were not stored.
    """

    def __init__(
        self,
        message: str = "Slurm entity was not created",
        missing: list[object] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.missing = missing or []
        super().__init__(message, errors, warnings, status_code)


class SlurmUserNotCreatedError(SlurmNotCreatedError):
    """One or more users were requested but not recorded in Slurm accounting.

    The most common cause is a missing OS account: slurmdbd resolves the
    user's uid against /etc/passwd and silently drops the write when the user
    does not exist on the cluster. Verify the OS account exists (e.g.
    ``useradd`` on the cluster nodes), then re-run.
    """

    def __init__(
        self,
        message: str = "Slurm user(s) were not recorded",
        missing: list[str] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, missing, errors, warnings, status_code)


class SlurmAccountNotCreatedError(SlurmNotCreatedError):
    """One or more accounts were requested but not recorded in Slurm accounting.

    Usually indicates the cluster rejected the account create (e.g. missing
    parent account in the hierarchy). Verify the account can be created on
    the cluster, then re-run.
    """

    def __init__(
        self,
        message: str = "Slurm account(s) were not recorded",
        missing: list[str] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, missing, errors, warnings, status_code)


class SlurmAssociationNotCreatedError(SlurmNotCreatedError):
    """One or more associations were requested but not recorded.

    Associations are hierarchical: a user-level association requires the
    parent account-level association to exist first, and slurmdbd resolves
    the user's uid from /etc/passwd. Either can cause a silent drop. Verify
    the parent association and the OS account exist, then re-run.
    """

    def __init__(
        self,
        message: str = "Slurm association(s) were not recorded",
        missing: list[tuple[str, str, str]] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, missing, errors, warnings, status_code)
