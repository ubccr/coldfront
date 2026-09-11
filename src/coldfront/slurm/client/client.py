# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm REST API client (version-agnostic).

Provides a single :class:`SlurmClient` that works across the supported
Slurm REST API versions. The version is negotiated once at connect time
via the ``/ping`` discovery endpoint; all subsequent calls use the same
version prefix.

Discovery is strict: it probes the supported API versions and refuses a
slurmrestd that exposes only unsupported ones.

Core entity schemas (``assoc_rec_set``, ``user``, ``account``,
``users_add_cond``, ``accounts_add_cond``) are stable across the supported
versions, so a single set of serializers handles them all without
conditional logic. Only the URL path prefix changes between versions — see
:ref:`version-agnostic-rest-client` in the design document.

Usage::

    client = SlurmClient(
        base_url="http://slurmrestd:8080",
        jwt_token="eyJhbGci...",
    )
    client.discover_version()

    # Create an association (nested assoc schema — see serialize_association)
    client.create_associations([{
        "account": "hpc-lab",
        "user": "jsmith",
        "cluster": "hpc01",
        "partition": "gpu",
        "shares_raw": 1,
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

import logging
import time
from typing import Any

import requests

from .exceptions import (
    SlurmAccountNotCreatedError,
    SlurmAssociationNotCreatedError,
    SlurmBadRequestError,
    SlurmError,
    SlurmUnavailableError,
    SlurmUserNotCreatedError,
)
from .versions import api_version_for, slurm_version_for, supported_api_versions

__all__ = [
    "SlurmClient",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP status codes used by slurmrestd
# ---------------------------------------------------------------------------
_HTTP_OK = 200
_HTTP_BAD_REQUEST = 400
_HTTP_UNPROCESSABLE = 422
_HTTP_BAD_GATEWAY = 502
_HTTP_SERVICE_UNAVAILABLE = 503
_HTTP_GATEWAY_TIMEOUT = 504

# Slurm error codes that map to specific exception types.
#
# Only codes the **supported slurmrestd versions actually emit** are mapped
# (verified live against the e2e stack). Auth (403) and not-found (404) and
# conflict (409) codes never occur on the supported versions — auth failures
# surface as 502/503 unavailability and missing entities as silent success —
# so they have no mapping and no exception class.
_ERROR_MAP: dict[str, type[SlurmError]] = {
    "ESLURM_REST_INVALID_QUERY": SlurmBadRequestError,
    "ESLURM_REST_FAIL_PARSING": SlurmBadRequestError,
    "ESLURM_REST_INVALID_JOBS_DESC": SlurmBadRequestError,
    "ESLURM_HTTP_INVALID_CONTENT_LENGTH": SlurmBadRequestError,
    "ESLURM_HTTP_INVALID_CONTENT_ENCODING": SlurmBadRequestError,
    "ESLURM_HTTP_UNEXPECTED_BODY": SlurmBadRequestError,
    "ESLURM_DATA_PARSE_BAD_INPUT": SlurmBadRequestError,
    "ESLURM_REST_BAD_REQUEST": SlurmBadRequestError,
    "ESLURM_DB_CONNECTION": SlurmUnavailableError,
    "SLURM_COMMUNICATIONS_CONNECTION_ERROR": SlurmUnavailableError,
    "SLURM_COMMUNICATIONS_SEND_ERROR": SlurmUnavailableError,
    "SLURM_COMMUNICATIONS_RECEIVE_ERROR": SlurmUnavailableError,
    "SLURMCTLD_COMMUNICATIONS_CONNECTION_ERROR": SlurmUnavailableError,
    "SLURMCTLD_COMMUNICATIONS_BACKOFF": SlurmUnavailableError,
    "SLURM_PROTOCOL_SOCKET_ZERO_BYTES_SENT": SlurmUnavailableError,
    "ESLURM_PROTOCOL_INCOMPLETE_PACKET": SlurmUnavailableError,
    "SLURM_PROTOCOL_SOCKET_IMPL_TIMEOUT": SlurmUnavailableError,
}

# Supported API versions in descending preference order, derived from the
# single source of truth in ``versions.py`` (release -> API mapping).
SUPPORTED_API_VERSIONS = supported_api_versions()

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
        version: Slurm release version (e.g. ``"25.11.8"``). If ``None``,
            call :meth:`discover_version` to negotiate the version. The
            REST API version is resolved internally and is not part of the
            public contract.
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
        self.version = version  # Slurm release (public); None => discover
        self._api_version = api_version_for(version) if version else None
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
        if self._api_version is None:
            self.discover_version()
        return f"{self.base_url}/slurm/{self._api_version}/{template}"

    def _slurmdb_path(self, template: str) -> str:
        """Build a path to the ``slurmdb`` API (slurmdbd endpoints)."""
        if self._api_version is None:
            self.discover_version()
        return f"{self.base_url}/slurmdb/{self._api_version}/{template}"

    # ------------------------------------------------------------------
    # Version discovery
    # ------------------------------------------------------------------

    def discover_version(self) -> str:
        """Discover the highest supported API version.

        Probes each known API version via ``GET /slurmdb/{version}/ping/``
        and selects the highest version that responds successfully. Stores
        the resolved REST API version in ``self._api_version`` and the
        corresponding Slurm release in ``self.version``.

        Returns:
            The chosen REST API version string (internal detail).

        Raises:
            RuntimeError: If no compatible version is found.
        """
        for v in SUPPORTED_API_VERSIONS:
            url = f"{self.base_url}/slurmdb/{v}/ping/"
            logger.debug("Probing API version %s at %s", v, url)
            try:
                resp = self.session.get(url, timeout=self.timeout)
                # Only a 2xx response means this API version actually exists.
                # A 404 (unknown version path) or 5xx (transient) must be
                # skipped so we fall back to a lower supported version.
                if 200 <= resp.status_code < 300:
                    self._api_version = v
                    self.version = slurm_version_for(v)
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

        raise RuntimeError(f"No compatible Slurm REST API version found (tried {SUPPORTED_API_VERSIONS})")

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

        All fields are stable across the supported API versions.

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
    def _tres_to_list(tres: dict[str, int]) -> list[dict[str, Any]]:
        """Convert a ``{type: count}`` TRES dict to the REST ``tres_list`` array format.

        The Slurm REST API expects TRES limits (``grptresmins``, ``grptres``,
        ``maxtresperjob``, ...) as an array of ``{type, count}`` objects, not a
        ``{type: count}`` dict. Verified live: sending a dict yields
        ``9208 Data parser expected a list``; the array form is accepted and
        stored (e.g. ``GrpTRESMins=billing=600000``).
        """
        return [{"type": k, "count": v} for k, v in tres.items()]

    @staticmethod
    def _set_nested(body: dict[str, Any], keys: list[str], value: Any) -> None:
        """Set ``value`` at a dotted path inside ``body``, creating dicts.

        The plain ``POST /associations/`` endpoint parses the nested
        ``assoc`` schema (e.g. ``max/tres/per/job``), so limit fields are
        placed at nested paths instead of flat top-level keys.
        """
        node = body
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value

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
        grp_tres_mins: dict[str, int] | None = None,
        grp_wall: int | None = None,
        qoslevel: list[str] | None = None,
    ) -> dict[str, Any]:
        """Serialize an association record for ``POST /associations/``.

        The ``associations`` endpoint parses the nested ``assoc`` schema
        (not the flat ``assoc_rec_set`` used by ``accounts_association``).
        Fields therefore live at nested paths: limits under ``max/``, the
        default QOS under ``default/qos``, and the association's QOS list
        under ``qos``. The flat ``assoc_rec_set`` names (``fairshare``,
        ``qoslevel``, ``parent``) are ignored by this endpoint, so they map
        to the nested equivalents (``shares_raw``, ``qos``,
        ``parent_account``).

        Args:
            account: Slurm account name.
            user: Slurm username.
            cluster: Cluster name.
            partition: Partition name (empty string for generic assoc).
            default_qos: Default QOS name (nested ``default.qos``).
            parent: Parent account name (``parent_account``).
            fairshare: Fairshare value (``shares_raw``).
            max_jobs: Maximum active jobs limit (``max.jobs.active``).
            max_submit_jobs: Maximum submit jobs limit (``max.jobs.total``).
            max_tres_per_job: Per-job TRES limits dict (e.g., {"node": 5});
                serialized to the ``tres_list`` array format
                (``max.tres.per.job``).
            max_tres_mins_per_job: Per-job TRES minutes limits dict;
                serialized to ``tres_list`` (``max.tres.minutes.per.job``).
            max_wall_duration_per_job: Max wall duration in minutes
                (``max.jobs.per.wall_clock``).
            grp_tres: Group TRES limits dict; serialized to ``tres_list``
                (``max.tres.total``).
            grp_tres_mins: Group TRES minutes limits dict (e.g., {"billing": N});
                serialized to ``tres_list`` (``max.tres.group.minutes``).
            grp_wall: Group wall duration limit in minutes
                (``max.per.account.wall_clock``).
            qoslevel: List of QOS names for this association (``qos``).

        Returns:
            A dict matching the nested ``assoc`` schema for ``POST /associations/``.
        """
        body: dict[str, Any] = {
            "account": account,
            "user": user,
            "cluster": cluster,
        }
        if partition:
            body["partition"] = partition
        if default_qos is not None:
            body["default"] = {"qos": default_qos}
        if parent is not None:
            body["parent_account"] = parent
        if fairshare is not None:
            body["shares_raw"] = fairshare
        # Limits live under the nested ``max`` object.
        if max_jobs is not None:
            SlurmClient._set_nested(body, ["max", "jobs", "active"], max_jobs)
        if max_submit_jobs is not None:
            SlurmClient._set_nested(body, ["max", "jobs", "total"], max_submit_jobs)
        if max_tres_per_job is not None:
            SlurmClient._set_nested(body, ["max", "tres", "per", "job"], SlurmClient._tres_to_list(max_tres_per_job))
        if max_tres_mins_per_job is not None:
            SlurmClient._set_nested(
                body,
                ["max", "tres", "minutes", "per", "job"],
                SlurmClient._tres_to_list(max_tres_mins_per_job),
            )
        if max_wall_duration_per_job is not None:
            SlurmClient._set_nested(body, ["max", "jobs", "per", "wall_clock"], max_wall_duration_per_job)
        if grp_tres is not None:
            SlurmClient._set_nested(body, ["max", "tres", "total"], SlurmClient._tres_to_list(grp_tres))
        if grp_tres_mins is not None:
            SlurmClient._set_nested(body, ["max", "tres", "group", "minutes"], SlurmClient._tres_to_list(grp_tres_mins))
        if grp_wall is not None:
            SlurmClient._set_nested(body, ["max", "per", "account", "wall_clock"], grp_wall)
        if qoslevel is not None:
            body["qos"] = qoslevel
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

        The ``default.qos`` field is included when provided.

        Args:
            name: Slurm username.
            default_account: User's default Slurm account name.
            default_wckey: Optional default wckey.
            default_qos: Optional default QOS name.
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
        compatible with the supported versions.

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
            A dict matching the ``openapi_users_add_cond_resp`` POST body:
            ``{user, association_condition}`` where ``association_condition``
            is the ``users_add_cond`` filter and ``user`` is the optional
            ``user_short`` (default account/wckey).
        """
        cond: dict[str, Any] = {
            "users": users,
        }
        if accounts is not None:
            cond["accounts"] = accounts
        if clusters is not None:
            cond["clusters"] = clusters
        if partitions is not None:
            cond["partitions"] = partitions
        if association is not None:
            cond["association"] = association
        if wckeys is not None:
            cond["wckeys"] = wckeys

        body: dict[str, Any] = {
            "association_condition": cond,
        }
        # user_short — the handler folds default account/wckey into the cond
        user_short: dict[str, Any] = {}
        if accounts:
            user_short["defaultaccount"] = accounts[0]
        if wckeys:
            user_short["defaultwckey"] = wckeys[0]
        if user_short:
            body["user"] = user_short
        return body

    @staticmethod
    def serialize_accounts_add_cond(
        accounts: list[str],
        clusters: list[str] | None = None,
        association: dict[str, Any] | None = None,
        description: str | None = None,
        organization: str | None = None,
    ) -> dict[str, Any]:
        """Serialize an ``accounts_add_cond`` for ``POST /accounts_association/``.

        Creates an account with an initial association in a single API call.

        Args:
            accounts: List of account names to add.
            clusters: List of cluster names to scope.
            association: Optional ``assoc_rec_set`` dict for the
                association parameters.
            description: Optional account description.
            organization: Optional account organization.

        Returns:
            A dict matching the ``openapi_accounts_add_cond_resp`` POST body:
            ``{account, association_condition}`` where ``association_condition``
            is the ``accounts_add_cond`` filter and ``account`` is the optional
            ``account_short`` (description/organization).
        """
        cond: dict[str, Any] = {
            "accounts": accounts,
        }
        if clusters is not None:
            cond["clusters"] = clusters
        if association is not None:
            cond["association"] = association

        body: dict[str, Any] = {
            "association_condition": cond,
        }
        # account_short — optional description/organization on the new account
        account_short: dict[str, Any] = {}
        if description is not None:
            account_short["description"] = description
        if organization is not None:
            account_short["organization"] = organization
        if account_short:
            body["account"] = account_short
        return body

    @staticmethod
    def serialize_qos(
        name: str,
        description: str | None = None,
        priority: int | None = None,
        limit_factor: float | None = None,
        max_submit_jobs_per_user: int | None = None,
        max_jobs_per_user: int | None = None,
        max_submit_jobs_per_account: int | None = None,
        max_jobs_per_account: int | None = None,
        max_wall_duration_per_job: int | None = None,
        grace_time: int | None = None,
    ) -> dict[str, Any]:
        """Serialize a QOS record for ``POST /slurmdb/{version}/qos/``.

        The limits are nested under a ``limits`` object
        (``limits/max/...``, ``limits/factor``, ``limits/grace_time``),
        matching the ``qos_rec`` parser schema; flat names such as
        ``maxwalldurationperjob`` are ignored.

        Args:
            name: QOS name.
            description: Optional QOS description.
            priority: Priority factor for the QOS.
            limit_factor: Factor applied to an association's group TRES limits.
            max_submit_jobs_per_user: Maximum pending or running jobs per user.
            max_jobs_per_user: Maximum running jobs per user.
            max_submit_jobs_per_account: Maximum pending or running jobs per account.
            max_jobs_per_account: Maximum running jobs per account.
            max_wall_duration_per_job: Maximum wall clock time per job in minutes.
            grace_time: Preemption grace time in seconds.

        Returns:
            A dict matching the ``qos_rec`` schema.
        """
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if priority is not None:
            body["priority"] = priority

        limits: dict[str, Any] = {}
        if grace_time is not None:
            limits["grace_time"] = grace_time
        if limit_factor is not None:
            limits["factor"] = limit_factor

        max_obj: dict[str, Any] = {}
        if max_submit_jobs_per_user is not None:
            SlurmClient._set_nested(max_obj, ["jobs", "per", "user"], max_submit_jobs_per_user)
        if max_jobs_per_user is not None:
            SlurmClient._set_nested(max_obj, ["jobs", "active_jobs", "per", "user"], max_jobs_per_user)
        if max_submit_jobs_per_account is not None:
            SlurmClient._set_nested(max_obj, ["jobs", "per", "account"], max_submit_jobs_per_account)
        if max_jobs_per_account is not None:
            SlurmClient._set_nested(max_obj, ["jobs", "active_jobs", "per", "account"], max_jobs_per_account)
        if max_wall_duration_per_job is not None:
            SlurmClient._set_nested(max_obj, ["wall_clock", "per", "job"], max_wall_duration_per_job)
        if max_obj:
            limits["max"] = max_obj

        if limits:
            body["limits"] = limits
        return body

    @staticmethod
    def serialize_partition(
        name: str,
        qos_allowed: str | None = None,
        qos_deny: str | None = None,
        qos_assigned: str | None = None,
        nodes_configured: str | None = None,
        tres_billing_weights: str | None = None,
    ) -> dict[str, Any]:
        """Serialize a partition record for ``POST /slurm/{version}/partitions/``.

        The data parser maps the nested ``qos/allowed`` (AllowQOS),
        ``qos/deny`` (DenyQOS) and ``qos/assigned`` (QOS) paths onto the
        partition's ``allow_qos``, ``deny_qos`` and ``qos`` fields,
        ``nodes/configured`` onto the partition's node list (``Nodes``), and
        ``tres/billing_weights`` onto ``TRESBillingWeights``. ``nodes`` is an
        object, not a plain string.

        Args:
            name: Partition name.
            qos_allowed: AllowQOS whitelist (comma-separated QOS names).
            qos_deny: DenyQOS blocklist (comma-separated QOS names).
            qos_assigned: QOS name whose limits apply to all jobs in the partition.
            nodes_configured: Comma-separated node names in the partition.
            tres_billing_weights: TRESBillingWeights string (e.g.
                ``"CPU=2.0,Node=3.0"``).

        Returns:
            A dict matching the ``partition_info`` schema for ``POST /partitions/``.
        """
        body: dict[str, Any] = {"name": name}
        if qos_allowed is not None or qos_deny is not None or qos_assigned is not None:
            qos: dict[str, Any] = {}
            if qos_allowed is not None:
                qos["allowed"] = qos_allowed
            if qos_deny is not None:
                qos["deny"] = qos_deny
            if qos_assigned is not None:
                qos["assigned"] = qos_assigned
            body["qos"] = qos
        if nodes_configured is not None:
            body["nodes"] = {"configured": nodes_configured}
        if tres_billing_weights is not None:
            body["tres"] = {"billing_weights": tres_billing_weights}
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
            SlurmError subclass corresponding to the error.
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

        # Fall back to HTTP status-based mapping. Only the statuses the
        # supported versions emit are mapped: 400/422 (bad request) and
        # 502/503/504 (unavailable). Auth (401/403), not-found (404) and
        # conflict (409) never occur live on the supported stack.
        if status == _HTTP_BAD_REQUEST or status == _HTTP_UNPROCESSABLE:
            raise SlurmBadRequestError(
                message="Bad request to Slurm API",
                errors=[str(e) for e in errors],
                warnings=[str(w) for w in warnings],
                status_code=status,
            )
        elif status in (_HTTP_BAD_GATEWAY, _HTTP_SERVICE_UNAVAILABLE, _HTTP_GATEWAY_TIMEOUT):
            raise SlurmUnavailableError(
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
            SlurmError subclass if the API returned an error.
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
            SlurmError subclass on failure.
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

            except SlurmUnavailableError as exc:
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
                    raise SlurmUnavailableError(
                        message=str(exc),
                        status_code=503,
                    ) from exc

            except SlurmError:
                # Non-transient error — re-raise immediately
                raise

        # Should not reach here (retries exhausted), but guard anyway
        if isinstance(last_exc, SlurmError):
            raise last_exc
        raise SlurmUnavailableError(
            message=f"Request failed after {self.retries} retries",
            status_code=503,
        )

    # ------------------------------------------------------------------
    # Silent-failure verification helpers
    # ------------------------------------------------------------------
    #
    # slurmdbd can silently no-op a create: HTTP 200, errors=[], but nothing
    # stored. Known causes: a user with no uid in /etc/passwd, an association
    # whose parent account association does not exist, or a user whose default
    # account is missing. The plain create endpoints return no data field to
    # inspect, so verification requires a read-back GET. The add_cond endpoints
    # return ``added_users``/``added_accounts`` on success and a completely
    # empty body on a silent no-op, so those can gate (skip the GET) on the
    # happy path and verify only when the body is empty (ambiguous between a
    # silent no-op and an already-present entity — the idempotent re-run case).

    def _verify_accounts_created(self, names: list[str]) -> None:
        """Confirm every requested account actually materialized.

        Accounts already present (including ones that pre-existed) count as
        success — this only flags accounts that never appeared.
        """
        got = self.get_accounts()
        present = {a.get("name", "") for a in got.get("accounts", [])}
        missing = [n for n in names if n not in present]
        if missing:
            raise SlurmAccountNotCreatedError(
                message=(
                    "Slurm account(s) were not recorded: "
                    + ", ".join(missing)
                    + ". Verify the cluster can create the account, then re-run."
                ),
                missing=missing,
            )

    def _verify_users_created(self, names: list[str]) -> None:
        """Confirm every requested user record actually materialized."""
        got = self.get_users()
        present = {u.get("name", "") for u in got.get("users", [])}
        missing = [n for n in names if n not in present]
        if missing:
            raise SlurmUserNotCreatedError(
                message=(
                    "Slurm user(s) were not recorded: "
                    + ", ".join(missing)
                    + ". Verify the OS account exists on the cluster "
                    + "(e.g. useradd), then re-run."
                ),
                missing=missing,
            )

    def _verify_associations_created(self, associations: list[dict[str, Any]]) -> None:
        """Confirm every requested association actually materialized.

        Associations are hierarchical, so the usual silent drops are a missing
        parent account-level association and a user with no uid. Each missing
        association is reported as ``(account, user, cluster)``.
        """
        got = self.get_associations()
        stored = [(a.get("account"), a.get("user", ""), a.get("cluster")) for a in got.get("associations", [])]
        missing = []
        for assoc in associations:
            key = (
                assoc.get("account"),
                assoc.get("user", ""),
                assoc.get("cluster"),
            )
            if key not in stored:
                missing.append(key)
        if missing:
            raise SlurmAssociationNotCreatedError(
                message=(
                    "Slurm association(s) were not recorded: "
                    + ", ".join(f"{a}/{u}/{c}" for a, u, c in missing)
                    + ". Verify the parent account association and the OS "
                    + "account exist, then re-run."
                ),
                missing=missing,
            )

    def _verify_users_have_associations(self, names: list[str]) -> None:
        """Confirm every requested user gained an association (add_cond path).

        ``users_association`` creates a user record *and* its user-level
        association; on a silent no-op nothing is stored, so an empty read-back
        of associations proves the failure. A user that already had any
        association counts as success (idempotent).
        """
        got = self.get_associations()
        present = {a.get("user", "") for a in got.get("associations", [])}
        missing = [n for n in names if n not in present]
        if missing:
            raise SlurmUserNotCreatedError(
                message=(
                    "Slurm user(s) did not gain an association: "
                    + ", ".join(missing)
                    + ". Verify the parent account association and the OS "
                    + "account exist, then re-run."
                ),
                missing=missing,
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

        Returns:
            Parsed response body.

        Note:
            Re-running this for an existing account is **silent success** on
            the live API (no already-exists error), and the verification
            read-back counts an already-present account as success, so this
            is naturally idempotent.
        """
        url = self._slurmdb_path("accounts/")
        logger.info("Creating %d Slurm accounts", len(accounts))
        # slurmrestd expects the account list wrapped in an ``accounts`` key
        body = self._request("POST", url, json_body={"accounts": accounts})
        # No data field on the plain endpoint — verify via read-back
        self._verify_accounts_created([a.get("name", "") for a in accounts])
        return body

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

        Note:
            Deleting a nonexistent account is **silent success** on the live
            API, and the live stack does not enforce default-account
            protection — it deletes an account even while it is a user's
            default.
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
        # slurmrestd expects the QOS list wrapped in a ``qos`` key
        return self._request("POST", url, json_body={"qos": qos_list})

    def delete_qos(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Delete a Slurm QOS definition.

        Corresponds to ``DELETE /slurmdb/{version}/qos/{name}``.

        Args:
            name: Name of the QOS to delete.

        Returns:
            Parsed response body.
        """
        url = self._slurmdb_path(f"qos/{name}")
        logger.info("Deleting QOS %s", name)
        return self._request("DELETE", url)

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

    def update_partitions(
        self,
        partitions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create or update Slurm partitions via the REST API.

        Corresponds to ``POST /slurm/{version}/partitions/``. Upserts
        existing partitions (e.g. setting ``AllowQOS``) and creates new
        partitions not present in slurm.conf. Changes are runtime-only:
        they are lost on ``scontrol reconfigure`` (which re-reads
        slurm.conf), so call :meth:`reconfigure` only *before* pushing, to
        load the QOS cache, and never after.

        Args:
            partitions: List of partition dicts from
                :meth:`serialize_partition`.

        Returns:
            Parsed response body (``errors``/``warnings``/``meta``).
        """
        url = self._slurm_path("partitions/")
        logger.info("Updating %d Slurm partitions", len(partitions))
        # slurmrestd expects the partition list wrapped in a ``partitions`` key
        return self._request("POST", url, json_body={"partitions": partitions})

    def delete_partition(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Delete a Slurm partition.

        Corresponds to ``DELETE /slurm/{version}/partition/{name}``.
        Used to tear down a runtime-created partition (e.g. one pushed by
        :meth:`update_partitions`) so the stack returns to its slurm.conf
        partition set.

        Args:
            name: Name of the partition to delete.

        Returns:
            Parsed response body.
        """
        url = self._slurm_path(f"partition/{name}")
        logger.info("Deleting partition %s", name)
        return self._request("DELETE", url)

    def reconfigure(self) -> dict[str, Any]:
        """Reconfigure slurmctld (re-read slurm.conf and reload caches).

        Corresponds to ``GET /slurm/{version}/reconfigure/``. Re-reading
        slurm.conf reverts any runtime-only partition changes made via
        :meth:`update_partitions` (AllowQOS, nodes, ...) back to the state
        declared in slurm.conf, so this is the natural way to reset the
        partition config to stock.

        Returns:
            Parsed response body (``errors``/``warnings``/``meta``).
        """
        url = self._slurm_path("reconfigure/")
        logger.info("Reconfiguring slurmctld")
        return self._request("GET", url)

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

        Note:
            Re-running this for an existing association is **silent success**
            on the live API (no already-exists error), and the verification
            read-back counts an already-present association as success, so
            this is naturally idempotent.
        """
        url = self._slurmdb_path("associations/")
        logger.info("Creating %d Slurm associations", len(associations))
        # slurmrestd expects the association list wrapped in an ``associations`` key
        body = self._request("POST", url, json_body={"associations": associations})
        # No data field on the plain endpoint — verify via read-back
        self._verify_associations_created(associations)
        return body

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
        # slurmrestd expects the user list wrapped in a ``users`` key
        body = self._request("POST", url, json_body={"users": users})
        # No data field on the plain endpoint — verify via read-back
        self._verify_users_created([u.get("name", "") for u in users])
        return body

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
        body = self._request("POST", url, json_body=users_add_cond)
        if body.get("added_users"):
            # Gate present — fresh adds confirmed by the response field (0 GETs)
            return body
        # Empty body is ambiguous (silent no-op vs already-exists): verify
        names = users_add_cond.get("association_condition", {}).get("users", [])
        self._verify_users_have_associations(names)
        return body

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
        body = self._request("POST", url, json_body=accounts_add_cond)
        if body.get("added_accounts"):
            # Gate present — fresh adds confirmed by the response field (0 GETs)
            return body
        # Empty body is ambiguous (silent no-op vs already-exists): verify
        names = accounts_add_cond.get("association_condition", {}).get("accounts", [])
        self._verify_accounts_created(names)
        return body

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
            SlurmError subclass if the API returned an error.
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
            Response body. Callers should check for ``"status"`` in the
            response and treat its absence as success if ``errors`` is
            empty.
        """
        url = self._slurm_path(f"job/{job_id}")
        params: dict[str, Any] = {"signal": signal}
        if flags is not None:
            params["flags"] = flags

        logger.info("Killing job %s with signal %s", job_id, signal)
        return self._request("DELETE", url, params=params)

    # ------------------------------------------------------------------
    # Job usage endpoints
    # ------------------------------------------------------------------

    def get_job_usage(
        self,
        start_time: int,
        end_time: int,
        cluster: str,
    ) -> list[dict[str, Any]]:
        """Query job records overlapping a usage window.

        Corresponds to ``GET /slurmdb/{version}/jobs/``.

        Uses the generic eligible-time overlap filter (``time_eligible``
        before ``end_time`` and ``time_end`` after ``start_time`` or still
        running), which works for any past day without needing job state
        filters. ``disable_truncate_usage_time`` is set so still-running
        jobs report full elapsed rather than truncating at the query time.

        Args:
            start_time: UNIX timestamp of the window start (inclusive).
            end_time: UNIX timestamp of the window end (exclusive).
            cluster: Cluster name to scope the query.

        Returns:
            List of job dicts overlapping the window. Pending jobs are
            filtered client-side by the caller.

        Raises:
            SlurmError subclass on failure.
        """
        url = self._slurmdb_path("jobs/")
        params: dict[str, Any] = {
            "start_time": str(start_time),
            "end_time": str(end_time),
            "cluster": cluster,
            "disable_truncate_usage_time": "true",
        }
        logger.info(
            "Querying jobs for cluster %s window [%d, %d)",
            cluster,
            start_time,
            end_time,
        )
        body = self._request("GET", url, params=params)
        return body.get("jobs", [])
