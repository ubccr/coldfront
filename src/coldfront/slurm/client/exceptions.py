# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm REST API exception hierarchy.

All Slurm REST API errors inherit from :class:`SlurmException`.
Callers can catch the base exception to handle any Slurm API failure,
or catch specific subclasses to react to particular error conditions.

Error codes from the Slurm source (``slurmdb_defs.h``, ``http.c``)
are mapped to HTTP status categories and raised as typed exceptions
by :class:`SlurmClient`.
"""

from __future__ import annotations


class SlurmException(Exception):
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


class SlurmAuthException(SlurmException):
    """Authentication or authorization failure.

    Raised when the JWT token is invalid, expired, or lacks the
    required Slurm admin privileges (403 Unauthorized/Forbidden).

    Maps to ``ESLURM_AUTH_CRED_INVALID``, ``ESLURM_AUTH_EXPIRED``,
    ``ESLURM_REST_AUTH_FAIL``.
    """

    def __init__(
        self,
        message: str = "Slurm authentication failed",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 403,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmBadRequestException(SlurmException):
    """Malformed request body or invalid query parameters.

    Raised when the API rejects the payload as invalid (400 Bad Request).

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


class SlurmNotFoundException(SlurmException):
    """Entity not found in Slurm accounting.

    Raised when a user, account, cluster, or other entity is not found
    (404 Not Found).

    Maps to ``ESLURM_INVALID_JOB_ID``, ``ESLURM_REST_UNKNOWN_URL``,
    ``ESLURM_USER_ID_MISSING``.
    """

    def __init__(
        self,
        message: str = "Slurm entity not found",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 404,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmConflictException(SlurmException):
    """Constraint violation or resource conflict.

    Raised when the API rejects an operation due to a duplicate entity,
    a default-account protection, or other data integrity conflict
    (409 Conflict).

    Subclasses provide more granular error handling.

    Maps to ``ESLURM_ALREADY_DB_ENTRY``, ``ESLURM_NO_REMOVE_DEFAULT_ACCOUNT``,
    ``ESLURM_NO_REMOVE_DEFAULT_QOS``.
    """

    def __init__(
        self,
        message: str = "Slurm resource conflict",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 409,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmUnavailableException(SlurmException):
    """Service unavailable or transient failure.

    Raised when ``slurmrestd`` cannot reach ``slurmdbd`` or the
    Slurm controller, or when a communication error occurs
    (503 Service Unavailable / 502 Bad Gateway).

    These are typically transient and should be retried with
    exponential backoff.

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


class SlurmInvalidQueryException(SlurmConflictException):
    """Ambiguous query matched multiple records.

    Raised when a query parameter matches more than one entity and
    the operation requires a single match.

    Maps to ``ESLURM_DATA_AMBIGUOUS_QUERY``.
    """

    def __init__(
        self,
        message: str = "Ambiguous Slurm query matched multiple records",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 409,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmUserIdMissingException(SlurmNotFoundException):
    """User not found in Slurm accounting.

    Raised when attempting to operate on a user that does not exist
    in the Slurm database.

    Maps to ``ESLURM_USER_ID_MISSING``.
    """

    def __init__(
        self,
        message: str = "Slurm user not found",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 404,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmNoRemoveDefaultAccountException(SlurmConflictException):
    """Cannot delete an account that is still a user's default.

    Raised when trying to delete an account that is set as the default
    account for one or more users. The caller must update those users'
    defaults first before retrying the delete.

    Maps to ``ESLURM_NO_REMOVE_DEFAULT_ACCOUNT``.
    """

    def __init__(
        self,
        message: str = "Account is still a user's default account",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 409,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)


class SlurmAlreadyExistsException(SlurmConflictException):
    """Entity already exists in Slurm accounting.

    Raised when trying to create an entity that already exists.
    This can be treated as success — the desired state is already
    present.

    Maps to ``ESLURM_ALREADY_DB_ENTRY``.
    """

    def __init__(
        self,
        message: str = "Slurm entity already exists",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        status_code: int | None = 409,
    ) -> None:
        super().__init__(message, errors, warnings, status_code)
