# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Pytest fixtures for the Slurm e2e suite.

Provides:

- ``slurm_stack`` — session-scoped, one real Slurm cluster per parametrized
  Slurm version (stock ``slurm.conf``; started once, torn down at session end).
  The origin ``slurm_acct_db`` is dumped once at startup so the generic
  cleanup can restore it.
- ``slurm_jwt`` — an admin JWT from ``scontrol token``.
- ``slurm_client`` — a :class:`SlurmClient` pointed at the live slurmrestd.
- ``slurm_settings`` — wires the live cluster into ``settings.SLURMRESTD_CLUSTERS``
  so ``sync_slurm_clusters`` / ``run_usage_sync`` talk to the real API unchanged.
- ``slurm_cleanup`` — autouse, restores the shared stack to its origin state
  after each test (see ``reset_slurm_stack``).
- ``submit_sleep_job`` — creates a live account+parent+user assoc and submits
  a real ``sleep N`` job as the baked-in ``cgray`` user (job submission needs
  a valid association because ``AccountingStorageEnforce=associations``).
"""

import re

import pytest
import semver
from django.test import override_settings

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.exceptions import SlurmError
from coldfront.slurm.client.versions import supported_slurm_versions
from tests.e2e.slurm.containers import SlurmStack

# Versions whose stacks we bring up. Each gets its own session-scoped stack.
# Derived from the canonical supported-versions source (client/versions.py).
SLURM_VERSIONS = list(supported_slurm_versions())

# A match expression is an optional comparison operator followed by a version:
# ``>=25.11.4``, ``>26.05.0``, ``26.11.1`` (bare = ``==``). See Version.match.
_MATCH_EXPR_RE = re.compile(r"^(<=|>=|==|!=|<|>)(.*)$")


def _normalize_version(v: str) -> str:
    """Strip leading zeros from numeric parts so the string is valid semver.

    Slurm pads the minor/patch parts (e.g. ``26.05.4``), but strict semver
    forbids leading zeros in numeric parts, so ``Version.parse("26.05.4")``
    raises. Normalizing ``05`` -> ``5`` yields ``26.5.4``, which parses and
    compares identically (05 == 5 numerically).
    """
    return ".".join(str(int(part)) if part.isdigit() else part for part in v.split("."))


def _normalize_expr(expr: str) -> str:
    """Normalize the version part of a match expression, keeping the operator."""
    match = _MATCH_EXPR_RE.match(expr)
    if match:
        op, ver = match.group(1), match.group(2)
        return f"{op}{_normalize_version(ver)}"
    return _normalize_version(expr)


def require_version(stack_or_version, *expressions) -> None:
    """Skip the current test unless the live Slurm version matches an expression.

    Version-gating helper for features that exist on only a subset of the
    supported Slurm versions (e.g. runtime partition config via
    ``POST /partitions/``, which v0.0.45 exposes but v0.0.44 does not).

    ``expressions`` are semver match expressions (``semver.Version.match``):
    ``>=25.11.4``, ``>26.05.0``, ``26.11.1`` (bare = ``==``), etc. The test
    runs if the live version satisfies **any** expression. Slurm's zero-padded
    minor/patch (``26.05.4``) is normalized to valid semver before comparing.

    Accepts either a :class:`SlurmStack` (reads ``.version``) or a raw version
    string, so it works both inside tests/fixtures that hold a stack and in
    fixtures that skip before starting one (only ``request.param``).

    Args:
        stack_or_version: A SlurmStack or a Slurm version string.
        expressions: Semver match expressions the version must satisfy.
    """
    version = getattr(stack_or_version, "version", stack_or_version)
    current = semver.Version.parse(_normalize_version(version))
    if not any(current.match(_normalize_expr(expr)) for expr in expressions):
        pytest.skip(f"requires Slurm matching {list(expressions)}; current {version}")


# The single base slurm.conf for every stack (see containers.py). Multiple
# stacks of the same version share it; ``variant`` keeps their projects/ports
# distinct. Future per-version confs would be added here as extra stems.
CONF_STOCK = "slurm.conf"

# The baked-in submit user (uid 1002) exists in /etc/passwd in all containers
# but has NO SlurmDB association; with AccountingStorageEnforce=associations
# a user-level assoc must exist for a job to submit. See submit_sleep_job.
SUBMIT_USER = "cgray"


@pytest.fixture(params=SLURM_VERSIONS, scope="session")
def slurm_stack(request) -> SlurmStack:
    """One real stock Slurm stack per version, started once per session."""
    stack = SlurmStack(version=request.param, slurm_conf=CONF_STOCK)
    try:
        stack.start()
    except Exception:
        stack.stop()
        raise
    _capture_origin_db(stack)
    request.addfinalizer(stack.stop)
    return stack


@pytest.fixture(scope="session")
def slurm_jwt(slurm_stack) -> str:
    """Admin JWT for the live stock cluster."""
    return slurm_stack.jwt()


@pytest.fixture(scope="session")
def slurm_client(slurm_stack, slurm_jwt) -> SlurmClient:
    """SlurmClient pointed at the live stock slurmrestd (version not pre-set)."""
    return SlurmClient(
        base_url=slurm_stack.restd_url(),
        jwt_token=slurm_jwt,
        timeout=30,
        retries=3,
        retry_backoff=1.5,
    )


@pytest.fixture(scope="session")
def slurm_settings(slurm_stack, slurm_jwt):
    """Point ``settings.SLURMRESTD_CLUSTERS`` at the live stock stack.

    ``build_client()`` reads this dict at call time, so the sync / usage code
    paths work against the real REST API without modification.
    """
    clusters = {
        "default": {
            "url": slurm_stack.restd_url(),
            "jwt_token": slurm_jwt,
            "version": "",
            "auth_type": "jwt",
            "timeout": 30,
            "retries": 3,
            "retry_backoff": 1.5,
        }
    }
    with override_settings(SLURMRESTD_CLUSTERS=clusters):
        yield clusters


# The MariaDB client runs inside the stack's ``mysql`` service; the compose
# env vars (MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE) are set there, so the
# commands use them rather than hardcoding credentials.
_DB_DUMP_FILE = "/tmp/origin-db.sql"


def _capture_origin_db(stack) -> None:
    """Dump the origin ``slurm_acct_db`` once at stack startup.

    The dump file lives in the stack's ``mysql`` container and is the baseline
    that ``reset_slurm_stack`` restores after every test. Captured right after
    start, before any test can pollute the DB.
    """
    cmd = f'mariadb-dump -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" > {_DB_DUMP_FILE}'
    out, err, rc = stack.exec("mysql", ["bash", "-c", cmd])
    if rc != 0:
        stack.stop()
        raise RuntimeError(f"origin mariadb dump failed (rc={rc}): {err.strip() or out.strip()}")


@pytest.fixture(autouse=True)
def slurm_cleanup(slurm_stack, slurm_client):
    """Restore the shared stock stack to its origin state after every e2e test.

    Autouse so a failing test can never leak state into the next one: teardown
    always runs. See :func:`reset_slurm_stack`.
    """
    yield
    reset_slurm_stack(slurm_stack, slurm_client)


def reset_slurm_stack(stack, client) -> None:
    """Reset a live Slurm stack to its origin state after a test.

    Generic per-test cleanup: kills any running jobs, restores the
    ``slurm_acct_db`` from the origin dump captured at startup, then
    reconfigures slurmctld so runtime partition changes are reverted to that
    stack's on-disk ``slurm.conf``. Identical for any stack, because
    reconfigure re-reads the stack's own conf and the DB restore is
    stack-local.

    Order is fixed: jobs must reach a terminal state before the DB restore
    (otherwise an in-flight job is orphaned), slurmdbd must be restarted after
    the restore so its assoc cache reloads from the restored DB, and
    reconfigure must run last to revert runtime partition changes.
    """
    # 1. Kill any running/pending jobs so the DB restore cannot orphan them.
    stack.exec(
        "slurmctld",
        ["bash", "-c", "scancel $(squeue -h -o '%i' | tr '\n' ' ') 2>/dev/null || true"],
    )
    # 2. Wait for all jobs to reach a terminal state.
    import time

    deadline = time.time() + 120
    while time.time() < deadline:
        out, _, _ = stack.exec("slurmctld", ["bash", "-c", "squeue -h -o '%T'"])
        if not out.strip():
            break
        time.sleep(2)
    # 3. Restore the origin slurm_acct_db (associations, users, QOS, job
    #    accounting) captured at stack startup.
    cmd = f'mariadb -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < {_DB_DUMP_FILE}'
    out, err, rc = stack.exec("mysql", ["bash", "-c", cmd])
    if rc != 0:
        raise RuntimeError(f"mariadb restore failed (rc={rc}): {err.strip() or out.strip()}")
    # 4. Restart slurmdbd so its assoc_mgr cache reloads from the restored DB.
    #
    # The raw mariadb restore leaves slurmdbd's in-memory association cache
    # stale: the users_association add_cond path (which requires the account-
    # level parent assoc to be present in that cache) silently drops the user
    # until the cache is reloaded. slurmdbd restart will clear the cache.
    _restart_slurmdbd(stack)
    # 5. Wait for slurmdbd to answer the REST API again (it reconnects on its
    # own; the client's retries absorb transient 502s while it boots).
    _wait_slurmdbd_ready(client)
    # 6. Reconfigure slurmctld to revert runtime partition changes.
    body = client.reconfigure()
    assert not body.get("errors"), f"reconfigure errors: {body.get('errors')}"


def _restart_slurmdbd(stack) -> None:
    """Restart the stack's slurmdbd process so its assoc cache reloads.

    With ``ALLOW_RESTARTS=true`` the slurmdbd container's PID 1 runs
    ``sleep infinity`` and slurmdbd itself is a child process, so we can kill
    just that process and re-exec ``gosu slurm /usr/sbin/slurmdbd -vvv`` in the
    same container — no container restart. The slurmdbd startup reloads its
    association cache from the DB, which is fixes any stale-cache issues after a
    raw mariadb restore.
    """
    import subprocess

    container = f"{stack.project_name}-slurmdbd"
    # Kill the slurmdbd process (precise pid from its pidfile; fall back to
    # pkill matching the process name exactly, which never matches the
    # entrypoint's `sleep infinity`/bash PID 1 process).
    cmd = (
        "pid=$(cat /var/run/slurm/slurmdbd.pid 2>/dev/null); "
        'if [ -n "$pid" ]; then kill $pid; else pkill -x slurmdbd; fi'
    )
    out, err, rc = stack.exec("slurmdbd", ["bash", "-c", cmd])
    if rc != 0:
        raise RuntimeError(f"failed to kill slurmdbd (rc={rc}): {err.strip() or out.strip()}")
    # Re-exec slurmdbd in the same container (detached).
    proc = subprocess.run(
        ["docker", "exec", "-d", container, "gosu", "slurm", "/usr/sbin/slurmdbd", "-vvv"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"docker exec slurmdbd failed (rc={proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )


def _wait_slurmdbd_ready(client, timeout_sec: int = 120) -> None:
    """Poll the REST API until slurmdbd answers again after a restart.

    slurmdbd reconnects to the API on its own; the client's retries absorb the
    transient 502s while it boots. Polling ``get_accounts`` until it succeeds
    signals the assoc cache is live.
    """
    import time

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            client.get_accounts()
            return
        except Exception:  # noqa: BLE001
            time.sleep(1)
    raise RuntimeError("slurmdbd did not come back after restart")


def create_live_account_for_job(stack, client, jwt, acct_name) -> None:
    """Create the live account + account-level parent + cgray user assoc.

    Job submission requires a valid association for the submit user:
    the add_cond endpoint creates the account + its account-level (parent)
    association in one call, and the plain create_associations endpoint adds
    the user-level assoc for the baked-in ``SUBMIT_USER``.
    """
    client.create_accounts_with_associations(
        client.serialize_accounts_add_cond(accounts=[acct_name], clusters=[stack.cluster_name()])
    )
    client.create_associations([{"account": acct_name, "user": SUBMIT_USER, "cluster": stack.cluster_name()}])


def submit_sleep_job(stack, acct_name, seconds=30, username=SUBMIT_USER) -> str:
    """Submit a real ``sleep N`` job as ``username``; returns the job id.

    ``acct_name`` is the Slurm account the submitter has access to (e.g. the
    ColdFront SlurmAccount linked to the allocation), passed as ``--account``.
    Runs inside slurmctld via ``runuser`` (the user must own a valid assoc in
    that account). Output goes to /dev/null because /data is root-owned and
    the submit user cannot write there (a job that cannot open its stdout file
    fails).
    """
    out, err, rc = stack.exec(
        "slurmctld",
        [
            "bash",
            "-c",
            f"cd /data && runuser -u {username} -- sbatch --partition=cpu "
            f"--account={acct_name} --job-name=e2e --output=/dev/null --wrap='sleep {seconds}' 2>&1",
        ],
    )
    if rc != 0:
        raise RuntimeError(f"sbatch failed (rc={rc}): {err.strip() or out.strip()}")
    if "Submitted batch job" not in out:
        raise RuntimeError(f"sbatch did not submit a job: {out.strip()!r}")
    return out.split("Submitted batch job", 1)[1].strip()


def wait_for_job_completion(stack, job_id, timeout_sec=120) -> None:
    """Poll slurmdbd until the job reaches COMPLETED/FAILED (terminal)."""
    import time

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        out, err, rc = stack.exec(
            "slurmdbd",
            ["bash", "-c", f"sacct -nP -j {job_id} --format=State | head -1"],
        )
        state = out.strip().split("|")[0] if out.strip() else ""
        if state in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"):
            return
        time.sleep(2)
    raise RuntimeError(f"job {job_id} did not reach a terminal state")


def client_assert_slurm_error(exc: Exception, expected: type[SlurmError] | None = None) -> None:
    """Assert an exception from the live API is a SlurmError subclass."""
    assert isinstance(exc, SlurmError), f"expected SlurmError, got {type(exc).__name__}"
    if expected is not None:
        assert isinstance(exc, expected)
