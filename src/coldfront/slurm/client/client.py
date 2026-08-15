# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm REST API client (version-agnostic).

Provides a single :class:`SlurmClient` that works with any Slurm REST API
version from v0.0.41 through v0.0.45. The version is negotiated once at
connect time via the ``/ping`` discovery endpoint; all subsequent calls
use the same version prefix.

Core entity schemas (``assoc_rec_set``, ``user``, ``account``,
``users_add_cond``, ``accounts_add_cond``) are stable across all versions,
so a single set of serializers handles every version without conditional
logic. Only the URL path prefix and two minor response-parsing details
change between versions — see :ref:`version-agnostic-rest-client` in the
design document.

Usage::

    client = SlurmClient(
        base_url="http://slurmrestd:8080",
        jwt_token="eyJhbGci...",
    )
    client.discover_version()

    # Create an association
    client.create_associations([{
        "account": "hpc-lab",
        "user": "jsmith",
        "cluster": "hpc01",
        "partition": "gpu",
        "fairshare": 1,
        ...
    }])

    # Kill running jobs for a user
    client.kill_jobs({
        "user_name": "jsmith",
        "account": "hpc-lab",
        "partition": "gpu",
        "signal": "SIGTERM",
    })
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from .exceptions import (
    SlurmAlreadyExistsException,
    SlurmAuthException,
    SlurmBadRequestException,
    SlurmConflictException,
    SlurmException,
    SlurmInvalidQueryException,
    SlurmNoRemoveDefaultAccountException,
    SlurmNotFoundException,
    SlurmUnavailableException,
    SlurmUserIdMissingException,
)

__all__ = [
    "SlurmClient",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP status codes used by slurmrestd
# ---------------------------------------------------------------------------
_HTTP_OK = 200
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_CONFLICT = 409
_HTTP_UNPROCESSABLE = 422
_HTTP_BAD_GATEWAY = 502
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_GATEWAY_TIMEOUT = 504

# Slurm error codes that map to specific exception types
# These are extracted from the C source (http.c, slurmdb_defs.h).
_ERROR_MAP: dict[str, type[SlurmException]] = {
    "ESLURM_REST_INVALID_QUERY": SlurmBadRequestException,
    "ESLURM_REST_FAIL_PARSING": SlurmBadRequestException,
    "ESLURM_REST_INVALID_JOBS_DESC": SlurmBadRequestException,
    "ESLURM_HTTP_INVALID_CONTENT_LENGTH": SlurmBadRequestException,
    "ESLURM_HTTP_INVALID_CONTENT_ENCODING": SlurmBadRequestException,
    "ESLURM_HTTP_UNEXPECTED_BODY": SlurmBadRequestException,
    "ESLURM_DATA_PARSE_BAD_INPUT": SlurmBadRequestException,
    "ESLURM_REST_BAD_REQUEST": SlurmBadRequestException,
    "ESLURM_AUTH_CRED_INVALID": SlurmAuthException,
    "ESLURM_AUTH_EXPIRED": SlurmAuthException,
    "ESLURM_REST_AUTH_FAIL": SlurmAuthException,
    "ESLURM_INVALID_JOB_ID": SlurmNotFoundException,
    "ESLURM_REST_UNKNOWN_URL": SlurmNotFoundException,
    "ESLURM_URL_INVALID_PATH": SlurmNotFoundException,
    "ESLURM_USER_ID_MISSING": SlurmUserIdMissingException,
    "ESLURM_NO_REMOVE_DEFAULT_ACCOUNT": SlurmNoRemoveDefaultAccountException,
    "ESLURM_NO_REMOVE_DEFAULT_QOS": SlurmConflictException,
    "ESLURM_ALREADY_DB_ENTRY": SlurmAlreadyExistsException,
    "ESLURM_DATA_AMBIGUOUS_QUERY": SlurmInvalidQueryException,
    "ESLURM_DATA_AMBIGUOUS_MODIFY": SlurmInvalidQueryException,
    "ESLURM_DB_CONNECTION": SlurmUnavailableException,
    "SLURM_COMMUNICATIONS_CONNECTION_ERROR": SlurmUnavailableException,
    "SLURM_COMMUNICATIONS_SEND_ERROR": SlurmUnavailableException,
    "SLURM_COMMUNICATIONS_RECEIVE_ERROR": SlurmUnavailableException,
    "SLURMCTLD_COMMUNICATIONS_CONNECTION_ERROR": SlurmUnavailableException,
    "SLURMCTLD_COMMUNICATIONS_BACKOFF": SlurmUnavailableException,
    "SLURM_PROTOCOL_SOCKET_ZERO_BYTES_SENT": SlurmUnavailableException,
    "ESLURM_PROTOCOL_INCOMPLETE_PACKET": SlurmUnavailableException,
    "SLURM_PROTOCOL_SOCKET_IMPL_TIMEOUT": SlurmUnavailableException,
    "EPERM": SlurmAuthException,
}

# Supported API versions in descending preference order
_SUPPORTED_VERSIONS = [
    "v0.0.45",
    "v0.0.44",
    "v0.0.43",
    "v0.0.42",
    "v0.0.41",
]

# Default config values
_DEFAULT_TIMEOUT = 30
_DEFAULT_RETRIES = 3
_DEFAULT_RETRY_BACKOFF = 1.5


class SlurmClient:
    """Slurm REST API client (version-agnostic).

    Provides typed access to all accounting endpoints ColdFront needs.
    The version is discovered at init time; the same entity serializers
    work for all supported versions.

    Parameters:
        base_url: Base URL of the ``slurmrestd`` instance (e.g.,
            ``http://slurmrestd:8080``).
        jwt_token: JWT token for a Slurm admin user.
        version: API version prefix to use. If ``None``, call
            :meth:`discover_version` to negotiate the version.
        timeout: HTTP request timeout in seconds (default 30).
        retries: Number of retry attempts on transient failures (default 3).
        retry_backoff: Exponential backoff base in seconds (default 1.5).
    """

    def __init__(
        self,
        base_url: str,
        jwt_token: str,
        version: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
        retry_backoff: float = _DEFAULT_RETRY_BACKOFF,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.version = version
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {jwt_token}",
            }
        )

        logger.info(
            "SlurmClient initialized: base_url=%s version=%s",
            self.base_url,
            self.version or "(not set, call discover_version)",
        )

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def _slurm_path(self, template: str) -> str:
        """Build a path to the ``slurm`` API (slurmctld endpoints)."""
        return f"{self.base_url}/slurm/{self.version}/{template}"

    def _slurmdb_path(self, template: str) -> str:
        """Build a path to the ``slurmdb`` API (slurmdbd endpoints)."""
        return f"{self.base_url}/slurmdb/{self.version}/{template}"

    # ------------------------------------------------------------------
    # Version discovery
    # ------------------------------------------------------------------

    def discover_version(self) -> str:
        """Discover the highest supported API version.

        Probes each known version via ``GET /slurmdb/{version}/ping/``
        and selects the highest version that responds successfully.
        Stores the chosen version in ``self.version``.

        Returns:
            The chosen version string (e.g., ``"v0.0.44"``).

        Raises:
            RuntimeError: If no compatible version is found.
        """
        for v in _SUPPORTED_VERSIONS:
            url = f"{self.base_url}/slurmdb/{v}/ping/"
            logger.debug("Probing API version %s at %s", v, url)
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code < 500:
                    self.version = v
                    logger.info(
                        "Negotiated API version %s (probed %s)",
                        v,
                        url,
                    )
                    return v
            except requests.RequestException as exc:
                logger.debug(
                    "Version %s probe failed: %s",
                    v,
                    exc,
                )
                continue

        raise RuntimeError(f"No compatible Slurm REST API version found (tried {_SUPPORTED_VERSIONS})")

    # ------------------------------------------------------------------
    # Serializers — single implementation for all versions
    # ------------------------------------------------------------------

    @staticmethod
    def serialize_account(
        name: str,
        description: str | None = None,
        organization: str | None = None,
    ) -> dict[str, Any]:
        """Serialize an account record for ``POST /accounts/``.

        Works for v0.0.41 through v0.0.45. All fields stable.

        Args:
            name: Slurm account name.
            description: Optional account description.
            organization: Optional organization string.

        Returns:
            A dict matching the ``account_rec`` schema.
        """
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if organization is not None:
            body["organization"] = organization
        return body

    @staticmethod
    def serialize_association(
        account: str,
        user: str,
        cluster: str,
        partition: str = "",
        default_qos: str | None = None,
        parent: str | None = None,
        fairshare: int | None = None,
        max_jobs: int | None = None,
        max_submit_jobs: int | None = None,
        max_tres_per_job: dict[str, int] | None = None,
        max_tres_mins_per_job: dict[str, int] | None = None,
        max_wall_duration_per_job: int | None = None,
        grp_tres: dict[str, int] | None = None,
        grp_wall: int | None = None,
        qoslevel: list[str] | None = None,
    ) -> dict[str, Any]:
        """Serialize an association record for ``POST /associations/``.

        Works for v0.0.41 through v0.0.45. All 22 ``assoc_rec_set``
        properties stable across versions.

        Args:
            account: Slurm account name.
            user: Slurm username.
            cluster: Cluster name.
            partition: Partition name (empty string for generic assoc).
            default_qos: Default QOS name.
            parent: Parent account name in the hierarchy.
            fairshare: Fairshare value (None = omit, uses Slurm default).
            max_jobs: Maximum active jobs limit.
            max_submit_jobs: Maximum submit jobs limit.
            max_tres_per_job: Per-job TRES limits dict (e.g., {"node": 5}).
            max_tres_mins_per_job: Per-job TRES minutes limits dict.
            max_wall_duration_per_job: Max wall duration in minutes.
            grp_tres: Group TRES limits dict.
            grp_wall: Group wall duration limit in minutes.
            qoslevel: List of QOS names for this association.
                Maps to ``assoc_rec_set.qoslevel`` in the REST API.

        Returns:
            A dict matching the ``assoc_rec_set`` schema.
        """
        body: dict[str, Any] = {
            "account": account,
            "user": user,
            "cluster": cluster,
            "partition": partition,
        }
        if default_qos is not None:
            body["defaultqos"] = default_qos
        if parent is not None:
            body["parent"] = parent
        if fairshare is not None:
            body["fairshare"] = fairshare
        if max_jobs is not None:
            body["maxjobs"] = max_jobs
        if max_submit_jobs is not None:
            body["maxsubmitjobs"] = max_submit_jobs
        if max_tres_per_job is not None:
            body["maxtresperjob"] = max_tres_per_job
        if max_tres_mins_per_job is not None:
            body["maxtresminsperjob"] = max_tres_mins_per_job
        if max_wall_duration_per_job is not None:
            body["maxwalldurationperjob"] = max_wall_duration_per_job
        if grp_tres is not None:
            body["grptres"] = grp_tres
        if grp_wall is not None:
            body["grpwall"] = grp_wall
        if qoslevel is not None:
            body["qoslevel"] = qoslevel
        return body

    @staticmethod
    def serialize_user(
        name: str,
        default_account: str,
        default_wckey: str | None = None,
        default_qos: str | None = None,
        admin_level: int = 0,
    ) -> dict[str, Any]:
        """Serialize a user record for ``POST /users/``.

        Works for v0.0.41 through v0.0.45. The ``default.qos`` field
        is included for v44+ but silently ignored by older versions.

        Args:
            name: Slurm username.
            default_account: User's default Slurm account name.
            default_wckey: Optional default wckey.
            default_qos: Optional default QOS name (v44+).
            admin_level: Slurm admin level (0=none, 1=operator, 2=admin).

        Returns:
            A dict matching the ``user_rec`` schema.
        """
        body: dict[str, Any] = {
            "name": name,
            "default": {
                "account": default_account,
                "wckey": default_wckey or "",
            },
        }
        if default_qos is not None:
            body["default"]["qos"] = default_qos
        if admin_level:
            body["administrator_level"] = admin_level
        return body

    @staticmethod
    def serialize_kill_jobs_msg(
        user_name: str | None = None,
        account: str | None = None,
        partition: str | None = None,
        signal: str = "SIGTERM",
        job_state: str | None = None,
        job_name: str | None = None,
        user_id: str | None = None,
        qos: str | None = None,
        reservation: str | None = None,
        wckey: str | None = None,
        nodes: str | None = None,
    ) -> dict[str, Any]:
        """Serialize a kill-jobs message for ``DELETE /jobs/``.

        ``job_state`` and ``flags`` are sent as simple strings,
        compatible with both the ref-object format (v41–v42) and
        inline-enum format (v43–v45).

        Args:
            user_name: Filter by username.
            account: Filter by account name.
            partition: Filter by partition name.
            signal: Signal to send (default ``"SIGTERM"``).
            job_state: Filter by job state string (e.g., ``"RUNNING"``).
            job_name: Filter by job name.
            user_id: Filter by user ID.
            qos: Filter by QOS.
            reservation: Filter by reservation.
            wckey: Filter by wckey.
            nodes: Filter by node list expression.

        Returns:
            A dict matching the ``kill_jobs_msg`` schema.
        """
        body: dict[str, Any] = {
            "signal": signal,
        }
        if user_name is not None:
            body["user_name"] = user_name
        if account is not None:
            body["account"] = account
        if partition is not None:
            body["partition"] = partition
        if job_state is not None:
            body["job_state"] = job_state
        if job_name is not None:
            body["job_name"] = job_name
        if user_id is not None:
            body["user_id"] = user_id
        if qos is not None:
            body["qos"] = qos
        if reservation is not None:
            body["reservation"] = reservation
        if wckey is not None:
            body["wckey"] = wckey
        if nodes is not None:
            body["nodes"] = nodes
        return body

    @staticmethod
    def serialize_users_add_cond(
        users: list[str],
        accounts: list[str] | None = None,
        clusters: list[str] | None = None,
        partitions: list[str] | None = None,
        association: dict[str, Any] | None = None,
        wckeys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Serialize a ``users_add_cond`` for ``POST /users_association/``.

        Creates a user with an initial association in a single API call.

        Args:
            users: List of usernames to add.
            accounts: List of account names to scope.
            clusters: List of cluster names to scope.
            partitions: List of partition names to scope.
            association: Optional ``assoc_rec_set`` dict for the
                association parameters.
            wckeys: List of wckey names.

        Returns:
            A dict matching the ``users_add_cond`` schema.
        """
        body: dict[str, Any] = {
            "users": users,
        }
        if accounts is not None:
            body["accounts"] = accounts
        if clusters is not None:
            body["clusters"] = clusters
        if partitions is not None:
            body["partitions"] = partitions
        if association is not None:
            body["association"] = association
        if wckeys is not None:
            body["wckeys"] = wckeys
        return body

    @staticmethod
    def serialize_accounts_add_cond(
        accounts: list[str],
        clusters: list[str] | None = None,
        association: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Serialize an ``accounts_add_cond`` for ``POST /accounts_association/``.

        Creates an account with an initial association in a single API call.

        Args:
            accounts: List of account names to add.
            clusters: List of cluster names to scope.
            association: Optional ``assoc_rec_set`` dict for the
                association parameters.

        Returns:
            A dict matching the ``accounts_add_cond`` schema.
        """
        body: dict[str, Any] = {
            "accounts": accounts,
        }
        if clusters is not None:
            body["clusters"] = clusters
        if association is not None:
            body["association"] = association
        return body

    @staticmethod
    def serialize_qos(
        name: str,
        description: str | None = None,
        priority: int | None = None,
        limit_factor: float | None = None,
        flags: list[str] | None = None,
        preempt: str | None = None,
        preempt_mode: str | None = None,
        grt_tres: dict[str, int] | None = None,
        grt_wall: int | None = None,
        max_tres_per_job: dict[str, int] | None = None,
        max_wall_duration_per_job: int | None = None,
        max_jobs: int | None = None,
        max_submit_jobs: int | None = None,
        max_tres_mins_per_job: dict[str, int] | None = None,
        min_tres_per_job: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Serialize a QOS record for ``POST /slurmdb/{version}/qos/``.

        Works for v0.0.41 through v0.0.45.

        Args:
            name: QOS name.
            description: Optional QOS description.
            priority: Priority value for the QOS.
            limit_factor: Limit factor.
            flags: List of QOS flags (e.g., "Denormal", "NoNormal").
            preempt: Preempting QOS name.
            preempt_mode: Preempt mode.
            grt_tres: Group TRES limits dict.
            grt_wall: Group wall limit in minutes.
            max_tres_per_job: Max TRES per job dict.
            max_wall_duration_per_job: Max wall duration in minutes.
            max_jobs: Max active jobs.
            max_submit_jobs: Max submit jobs.
            max_tres_mins_per_job: Max TRES minutes per job.
            min_tres_per_job: Min TRES per job dict.

        Returns:
            A dict matching the ``qos_rec`` schema.
        """
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if priority is not None:
            body["priority"] = priority
        if limit_factor is not None:
            body["limit_factor"] = limit_factor
        if flags is not None:
            body["flags"] = flags
        if preempt is not None:
            body["preempt"] = preempt
        if preempt_mode is not None:
            body["preemptmode"] = preempt_mode
        if grt_tres is not None:
            body["grptres"] = grt_tres
        if grt_wall is not None:
            body["grpwall"] = grt_wall
        if max_tres_per_job is not None:
            body["maxtresperjob"] = max_tres_per_job
        if max_wall_duration_per_job is not None:
            body["maxwalldurationperjob"] = max_wall_duration_per_job
        if max_jobs is not None:
            body["maxjobs"] = max_jobs
        if max_submit_jobs is not None:
            body["maxsubmitjobs"] = max_submit_jobs
        if max_tres_mins_per_job is not None:
            body["maxtresminsperjob"] = max_tres_mins_per_job
        if min_tres_per_job is not None:
            body["mintresperjob"] = min_tres_per_job
        return body

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _raise_for_error(
        self,
        resp: requests.Response,
        body: dict[str, Any],
    ) -> None:
        """Raise a typed exception if the response indicates an error.

        Parses the ``errors`` array from the response body and maps
        known Slurm error codes to specific exception types. If no
        error code matches, falls back to HTTP status-based mapping.

        Args:
            resp: The HTTP response object.
            body: Parsed JSON body (may be empty).

        Raises:
            SlurmException subclass corresponding to the error.
        """
        status = resp.status_code
        errors = body.get("errors", [])
        warnings = body.get("warnings", [])

        # If there are no errors and status is OK, nothing to raise
        if status < 400 and not errors:
            return

        # Log warnings regardless of error presence
        for w in warnings:
            logger.warning("Slurm API warning: %s", w)

        # Try to map error codes from the errors array
        for err in errors:
            if isinstance(err, dict):
                error_number = err.get("error_number", err.get("num"))
                description = err.get("error", err.get("description", ""))
                err_code = err.get("error", "")
                source = err.get("source", "")
            else:
                error_number = None
                description = str(err)
                err_code = ""
                source = ""

            # Map known error codes to exception types
            if err_code and err_code in _ERROR_MAP:
                exc_class = _ERROR_MAP[err_code]
                logger.error(
                    "Slurm API error [%s]: %s (source=%s)",
                    err_code,
                    description,
                    source,
                )
                raise exc_class(
                    message=description or "Slurm API error",
                    errors=[str(e) for e in errors],
                    warnings=[str(w) for w in warnings],
                    status_code=status,
                )

            # Map error numbers if present (e.g., from openapi_error.error_number)
            if error_number is not None:
                logger.error(
                    "Slurm API error_number=%d: %s",
                    error_number,
                    description,
                )

        # Fall back to HTTP status-based mapping
        if status == _HTTP_BAD_REQUEST or status == _HTTP_UNPROCESSABLE:
            raise SlurmBadRequestException(
                message="Bad request to Slurm API",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )
        elif status in (_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN):
            raise SlurmAuthException(
                message="Authentication/authorization failure",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )
        elif status == _HTTP_NOT_FOUND:
            raise SlurmNotFoundException(
                message="Entity not found in Slurm",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )
        elif status == _HTTP_CONFLICT:
            raise SlurmConflictException(
                message="Resource conflict",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )
        elif status in (_HTTP_BAD_GATEWAY, _HTTP_SERVICE_UNAVAILABLE, _HTTP_GATEWAY_TIMEOUT):
            raise SlurmUnavailableException(
                message="Slurm service unavailable or timed out",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )

    def _parse_response(
        self,
        resp: requests.Response,
    ) -> dict[str, Any]:
        """Parse a Slurm API response.

        Extracts ``errors``, ``warnings``, ``meta``, ``status``, and
        any entity data (``accounts``, ``associations``, ``users``, etc.)
        from the JSON body.

        Raises a typed exception if the response indicates an error.

        Args:
            resp: The HTTP response object.

        Returns:
            The parsed JSON body dict. Callers can then extract
            entity-specific fields (e.g., ``body["associations"]``).

        Raises:
            SlurmException subclass if the API returned an error.
        """
        body: dict[str, Any] = {}
        if resp.content:
            try:
                body = resp.json()
            except ValueError as exc:
                logger.warning(
                    "Failed to parse Slurm response body as JSON: %s",
                    exc,
                )

        self._raise_for_error(resp, body)

        # Log warnings
        for w in body.get("warnings", []):
            logger.warning("Slurm API warning: %s", w)

        return body

    def _request(
        self,
        method: str,
        url: str,
        json_body: dict[str, Any] | list[dict[str, Any]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a request with retry logic for transient failures.

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, ``"DELETE"``).
            url: Full URL to request.
            json_body: JSON-serializable body to send.
            params: Query parameters dict.

        Returns:
            Parsed response body dict.

        Raises:
            SlurmException subclass on failure.
        """
        last_exc: Exception | None = None
        last_body: dict[str, Any] = {}

        for attempt in range(1, self.retries + 1):
            try:
                logger.debug(
                    "%s %s (attempt %d/%d)",
                    method,
                    url,
                    attempt,
                    self.retries,
                )
                resp = self.session.request(
                    method=method,
                    url=url,
                    json=json_body,
                    params=params,
                    timeout=self.timeout,
                )
                last_body = self._parse_response(resp)
                return last_body

            except SlurmUnavailableException as exc:
                # Transient — retry with backoff
                last_exc = exc
                last_body = exc.errors or []
                logger.warning(
                    "Slurm transient failure (attempt %d/%d): %s",
                    attempt,
                    self.retries,
                    exc,
                )
                if attempt < self.retries:
                    backoff = self.retry_backoff * (2 ** (attempt - 1))
                    time.sleep(backoff)
                else:
                    raise

            except requests.RequestException as exc:
                # Network-level failure
                last_exc = exc
                logger.error(
                    "Slurm request failed (attempt %d/%d): %s",
                    attempt,
                    self.retries,
                    exc,
                )
                if attempt < self.retries:
                    backoff = self.retry_backoff * (2 ** (attempt - 1))
                    time.sleep(backoff)
                else:
                    raise SlurmUnavailableException(
                        message=str(exc),
                        status_code=503,
                    ) from exc

            except SlurmException:
                # Non-transient error — re-raise immediately
                raise

        # Should not reach here (retries exhausted), but guard anyway
        if isinstance(last_exc, SlurmException):
            raise last_exc
        raise SlurmUnavailableException(
            message=f"Request failed after {self.retries} retries",
            status_code=503,
        )

    # ------------------------------------------------------------------
    # Account endpoints
    # ------------------------------------------------------------------

    def create_accounts(
        self,
        accounts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or update Slurm accounts.

        Corresponds to ``POST /slurmdb/{version}/accounts/``.

        Args:
            accounts: List of account dicts from :meth:`serialize_account`.

        Returns:
            Parsed response body.

        Raises:
            SlurmConflictException: If an account already exists
                (use :meth:`create_accounts_with_conflict_ok` if desired).
        """
        url = self._slurmdb_path("accounts/")
        logger.info("Creating %d Slurm accounts", len(accounts))
        return self._request("POST", url, json_body=accounts)

    def create_accounts_with_conflict_ok(
        self,
        accounts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create accounts, treating ``ESLURM_ALREADY_DB_ENTRY`` as success.

        Wrapper around :meth:`create_accounts` that catches the
        already-exists exception and returns the response body.

        Args:
            accounts: List of account dicts from :meth:`serialize_account`.

        Returns:
            Parsed response body (or a dict with ``errors`` if conflict).
        """
        try:
            return self.create_accounts(accounts)
        except SlurmAlreadyExistsException as exc:
            logger.info(
                "Accounts already exist (treated as success): %s",
                exc,
            )
            return {
                "errors": exc.errors,
                "warnings": exc.warnings,
            }

    def get_accounts(
        self,
        name: str | None = None,
        with_assocs: bool = False,
        with_deleted: bool = False,
    ) -> dict[str, Any]:
        """Query Slurm accounts.

        Corresponds to ``GET /slurmdb/{version}/accounts/``.

        Args:
            name: Filter by account name.
            with_assocs: Include association data.
            with_deleted: Include deleted accounts.

        Returns:
            Response body containing ``accounts`` list.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if with_assocs:
            params["with_assocs"] = "true"
        if with_deleted:
            params["with_deleted"] = "true"

        url = self._slurmdb_path("accounts/")
        logger.debug("Querying accounts: %s", params)
        return self._request("GET", url, params=params)

    def delete_account(
        self,
        account_name: str,
        cluster: str,
    ) -> dict[str, Any]:
        """Delete a Slurm account.

        Corresponds to ``DELETE /slurmdb/{version}/account/{name}``.

        Args:
            account_name: Name of the account to delete.
            cluster: Cluster the account belongs to.

        Returns:
            Parsed response body.

        Raises:
            SlurmNoRemoveDefaultAccountException: If the account is
                still a user's default account.
        """
        url = self._slurmdb_path(f"account/{account_name}")
        params = {"cluster": cluster}
        logger.info("Deleting account %s on cluster %s", account_name, cluster)
        return self._request("DELETE", url, params=params)

    # ------------------------------------------------------------------
    # QOS endpoints
    # ------------------------------------------------------------------

    def get_qos(
        self,
        name: str | None = None,
        with_deleted: bool = False,
    ) -> dict[str, Any]:
        """Query Slurm QOS definitions.

        Corresponds to ``GET /slurmdb/{version}/qos/``.

        Args:
            name: Filter by QOS name.
            with_deleted: Include deleted QOS.

        Returns:
            Response body containing ``qos`` list.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if with_deleted:
            params["with_deleted"] = "true"

        url = self._slurmdb_path("qos/")
        logger.debug("Querying QOS: %s", params)
        return self._request("GET", url, params=params)

    def upsert_qos(
        self,
        qos_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or update Slurm QOS definitions.

        Corresponds to ``POST /slurmdb/{version}/qos/``.

        Args:
            qos_list: List of QOS dicts from :meth:`serialize_qos`.

        Returns:
            Parsed response body.
        """
        url = self._slurmdb_path("qos/")
        logger.info("Upserting %d QOS definitions", len(qos_list))
        return self._request("POST", url, json_body=qos_list)

    # ------------------------------------------------------------------
    # Partition endpoints (slurmctld)
    # ------------------------------------------------------------------

    def get_partitions(
        self,
        partition_name: str | None = None,
        **params: str,
    ) -> dict[str, Any]:
        """Get partition info from slurmctld.

        Corresponds to ``GET /slurm/{version}/partitions/``.

        Args:
            partition_name: Filter by partition name.
            **params: Additional query parameters.

        Returns:
            Response body containing ``partitions`` list.
        """
        url = self._slurm_path("partitions/")
        if partition_name is not None:
            url = self._slurm_path(f"partition/{partition_name}")
        logger.debug("Querying partitions: %s", params)
        return self._request("GET", url, params=params or None)

    def get_nodes(
        self,
        node_name: str | None = None,
        **params: str,
    ) -> dict[str, Any]:
        """Get node info from slurmctld.

        Corresponds to ``GET /slurm/{version}/nodes/``.

        Args:
            node_name: Filter by node name.
            **params: Additional query parameters.

        Returns:
            Response body containing ``nodes`` list.
        """
        url = self._slurm_path("nodes/")
        if node_name is not None:
            url = self._slurm_path(f"node/{node_name}")
        logger.debug("Querying nodes: %s", params)
        return self._request("GET", url, params=params or None)

    # ------------------------------------------------------------------
    # Association endpoints
    # ------------------------------------------------------------------

    def create_associations(
        self,
        associations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or update Slurm associations.

        Corresponds to ``POST /slurmdb/{version}/associations/``.

        Args:
            associations: List of association dicts from
                :meth:`serialize_association`.

        Returns:
            Parsed response body.

        Raises:
            SlurmAlreadyExistsException: If an association already exists
                (use :meth:`create_associations_with_conflict_ok` if desired).
        """
        url = self._slurmdb_path("associations/")
        logger.info("Creating %d Slurm associations", len(associations))
        return self._request("POST", url, json_body=associations)

    def create_associations_with_conflict_ok(
        self,
        associations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create associations, treating ``ESLURM_ALREADY_DB_ENTRY`` as success.

        Wrapper around :meth:`create_associations` that catches the
        already-exists exception.

        Args:
            associations: List of association dicts.

        Returns:
            Parsed response body (or dict with ``errors`` if conflict).
        """
        try:
            return self.create_associations(associations)
        except SlurmAlreadyExistsException as exc:
            logger.info(
                "Associations already exist (treated as success): %s",
                exc,
            )
            return {
                "errors": exc.errors,
                "warnings": exc.warnings,
            }

    def get_associations(
        self,
        account: str | None = None,
        user: str | None = None,
        cluster: str | None = None,
        partition: str | None = None,
        with_deleted: bool = False,
    ) -> dict[str, Any]:
        """Query Slurm associations.

        Corresponds to ``GET /slurmdb/{version}/associations/``.

        Args:
            account: Filter by account name.
            user: Filter by username.
            cluster: Filter by cluster name.
            partition: Filter by partition name.
            with_deleted: Include deleted associations.

        Returns:
            Response body containing ``associations`` list.
        """
        params: dict[str, Any] = {}
        if account is not None:
            params["account"] = account
        if user is not None:
            params["user"] = user
        if cluster is not None:
            params["cluster"] = cluster
        if partition is not None:
            params["partition"] = partition
        if with_deleted:
            params["with_deleted"] = "true"

        url = self._slurmdb_path("associations/")
        logger.debug("Querying associations: %s", params)
        return self._request("GET", url, params=params)

    def delete_associations(
        self,
        account: str,
        user: str,
        cluster: str,
        partition: str | None = None,
    ) -> dict[str, Any]:
        """Delete Slurm associations matching the filter.

        Corresponds to ``DELETE /slurmdb/{version}/associations/``.

        Args:
            account: Account name filter.
            user: Username filter.
            cluster: Cluster name filter.
            partition: Partition name filter (optional).

        Returns:
            Parsed response body.
        """
        params: dict[str, Any] = {
            "account": account,
            "user": user,
            "cluster": cluster,
        }
        if partition is not None:
            params["partition"] = partition

        url = self._slurmdb_path("associations/")
        logger.info(
            "Deleting associations: account=%s user=%s cluster=%s partition=%s",
            account,
            user,
            cluster,
            partition or "(generic)",
        )
        return self._request("DELETE", url, params=params)

    # ------------------------------------------------------------------
    # User endpoints
    # ------------------------------------------------------------------

    def create_users(
        self,
        users: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or update Slurm users.

        Corresponds to ``POST /slurmdb/{version}/users/``.

        Args:
            users: List of user dicts from :meth:`serialize_user`.

        Returns:
            Parsed response body.
        """
        url = self._slurmdb_path("users/")
        logger.info("Creating %d Slurm users", len(users))
        return self._request("POST", url, json_body=users)

    def get_users(
        self,
        name: str | None = None,
        with_assocs: bool = False,
        with_deleted: bool = False,
    ) -> dict[str, Any]:
        """Query Slurm users.

        Corresponds to ``GET /slurmdb/{version}/users/``.

        Args:
            name: Filter by username.
            with_assocs: Include association data.
            with_deleted: Include deleted users.

        Returns:
            Response body containing ``users`` list.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if with_assocs:
            params["with_assocs"] = "true"
        if with_deleted:
            params["with_deleted"] = "true"

        url = self._slurmdb_path("users/")
        logger.debug("Querying users: %s", params)
        return self._request("GET", url, params=params)

    def delete_user(
        self,
        username: str,
        cluster: str,
    ) -> dict[str, Any]:
        """Delete a Slurm user.

        Corresponds to ``DELETE /slurmdb/{version}/user/{name}``.

        Args:
            username: Username to delete.
            cluster: Cluster the user belongs to.

        Returns:
            Parsed response body.
        """
        url = self._slurmdb_path(f"user/{username}")
        params = {"cluster": cluster}
        logger.info("Deleting user %s on cluster %s", username, cluster)
        return self._request("DELETE", url, params=params)

    # ------------------------------------------------------------------
    # User + Association shortcuts (bulk create)
    # ------------------------------------------------------------------

    def create_users_with_associations(
        self,
        users_add_cond: dict[str, Any],
    ) -> dict[str, Any]:
        """Create users with initial associations in one call.

        Corresponds to ``POST /slurmdb/{version}/users_association/``.

        Args:
            users_add_cond: Dict from :meth:`serialize_users_add_cond`.

        Returns:
            Response body containing ``added_users`` list.
        """
        url = self._slurmdb_path("users_association/")
        logger.info("Creating users with associations")
        return self._request("POST", url, json_body=users_add_cond)

    def create_accounts_with_associations(
        self,
        accounts_add_cond: dict[str, Any],
    ) -> dict[str, Any]:
        """Create accounts with initial associations in one call.

        Corresponds to ``POST /slurmdb/{version}/accounts_association/``.

        Args:
            accounts_add_cond: Dict from :meth:`serialize_accounts_add_cond`.

        Returns:
            Response body containing ``added_accounts`` list.
        """
        url = self._slurmdb_path("accounts_association/")
        logger.info("Creating accounts with associations")
        return self._request("POST", url, json_body=accounts_add_cond)

    # ------------------------------------------------------------------
    # Config endpoints
    # ------------------------------------------------------------------

    def get_config(self) -> dict[str, Any]:
        """Get current SlurmDBD accounting configuration.

        Corresponds to ``GET /slurmdb/{version}/config``.

        Returns:
            Response body containing all accounting entities
            (``accounts``, ``associations``, ``users``, ``clusters``,
            ``qos``, ``tres``, etc.).
        """
        url = self._slurmdb_path("config")
        logger.debug("Fetching SlurmDBD config")
        return self._request("GET", url)

    def upsert_config(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert the full SlurmDBD accounting configuration.

        Corresponds to ``POST /slurmdb/{version}/config``.

        Sends the complete desired accounting state (clusters, accounts,
        users, associations, QOS, TRES, wckeys) to slurmdbd.  Slurmdbd
        creates missing entities and updates existing ones — this is an
        upsert-only operation (no deletions).

        Args:
            config: A dict matching ``openapi_slurmdbd_config_resp``
                schema, typically built by :meth:`serialize_config`.
                Expected keys: ``clusters``, ``accounts``, ``users``,
                ``associations``, ``qos``, ``tres``, ``wckeys``.

        Returns:
            Response body with ``errors``, ``warnings``, and ``meta``.

        Raises:
            SlurmException subclass if the API returned an error.
        """
        url = self._slurmdb_path("config")
        logger.info("Upserting SlurmDBD accounting config")
        return self._request("POST", url, json_body=config)

    @staticmethod
    def serialize_config(
        *,
        clusters: list[dict[str, Any]] | None = None,
        accounts: list[dict[str, Any]] | None = None,
        users: list[dict[str, Any]] | None = None,
        associations: list[dict[str, Any]] | None = None,
        qos: list[dict[str, Any]] | None = None,
        tres: list[dict[str, Any]] | None = None,
        wckeys: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Serialize a full accounting config payload for ``POST /config``.

        Builds a dict matching the ``openapi_slurmdbd_config_resp``
        schema expected by slurmdbd's upsert endpoint.  Each entity
        list is optional — only the provided entity types are upserted.

        Args:
            clusters: List of cluster dicts.
            accounts: List of account dicts (from :meth:`serialize_account`).
            users: List of user dicts (from :meth:`serialize_user`).
            associations: List of association dicts
                (from :meth:`serialize_association`).
            qos: List of QOS dicts.
            tres: List of TRES dicts.
            wckeys: List of wckey dicts.

        Returns:
            A dict suitable as the body of ``POST /config``.
        """
        body: dict[str, Any] = {}
        if clusters is not None:
            body["clusters"] = clusters
        if accounts is not None:
            body["accounts"] = accounts
        if users is not None:
            body["users"] = users
        if associations is not None:
            body["associations"] = associations
        if qos is not None:
            body["qos"] = qos
        if tres is not None:
            body["tres"] = tres
        if wckeys is not None:
            body["wckeys"] = wckeys
        return body

    def dump_config(
        self,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request a config dump from slurmdbd.

        Corresponds to ``POST /slurmdb/{version}/config``.

        .. deprecated::
            Use :meth:`get_config` (GET) for fetching config or
            :meth:`upsert_config` (POST) for applying config.
            This method exists for backward compatibility; it sends a
            POST with a body that slurmdbd interprets as an upsert
            payload, not a dump request.

        Args:
            body: Optional request body.  If provided, slurmdbd treats
                it as an upsert payload (same as :meth:`upsert_config`).

        Returns:
            Response body.
        """
        url = self._slurmdb_path("config")
        logger.warning("dump_config() is deprecated — use get_config() or upsert_config()")
        return self._request("POST", url, json_body=body)

    # ------------------------------------------------------------------
    # Job kill endpoints
    # ------------------------------------------------------------------

    def kill_jobs(
        self,
        kill_msg: dict[str, Any],
    ) -> dict[str, Any]:
        """Kill running jobs matching the filter criteria.

        Corresponds to ``DELETE /slurm/{version}/jobs/``.

        Args:
            kill_msg: Dict from :meth:`serialize_kill_jobs_msg`.

        Returns:
            Response body containing ``status`` and ``errors``.
        """
        url = self._slurm_path("jobs/")
        logger.info("Killing jobs: %s", kill_msg)
        return self._request("DELETE", url, json_body=kill_msg)

    def kill_job(
        self,
        job_id: str,
        signal: str = "SIGTERM",
        flags: str | None = None,
    ) -> dict[str, Any]:
        """Kill a specific job by ID.

        Corresponds to ``DELETE /slurm/{version}/job/{job_id}``.

        Args:
            job_id: Slurm job ID string.
            signal: Signal to send (default ``"SIGTERM"``).
            flags: Optional kill flags.

        Returns:
            Response body. Note: v0.0.41 does not include a ``status``
            field in the response; v0.0.42+ does. Callers should check
            for ``"status"`` in the response and treat its absence as
            success if ``errors`` is empty.
        """
        url = self._slurm_path(f"job/{job_id}")
        params: dict[str, Any] = {"signal": signal}
        if flags is not None:
            params["flags"] = flags

        logger.info("Killing job %s with signal %s", job_id, signal)
        return self._request("DELETE", url, params=params)
