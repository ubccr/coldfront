# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live Slurm access-control e2e test (partition ``AllowQOS`` whitelist).

Verifies that partition ``AllowQOS`` pushed at runtime via the REST API
(``POST /partitions/`` -> ``qos/allowed``) is enforced at job submission:

* a job whose resolved QOS is **not** in a partition's ``AllowQOS`` list is
  rejected at submit (rc != 0 — the "Invalid account or account/partition
  combination specified" error, which is Slurm's no-QOS-access message), and
* a job whose QOS **is** allowed is accepted.

The stock ``slurm.conf`` has no baked-in ``AllowQOS``, so the test creates its
own runtime ``q2`` partition via the REST API (sharing node ``c1`` with the
existing ``cpu`` partition so it is submit-able under ``EnforcePartLimits``)
and pushes ``AllowQOS=cpu`` on the existing ``cpu`` partition. Teardown deletes
the runtime ``q2`` partition and reconfigures slurmctld, which re-reads
slurm.conf and restores ``cpu`` to its stock state.

Requires ``EnforcePartLimits=ANY`` (or YES) in slurm.conf: the submit-time
AllowQOS check in ``job_mgr.c`` is gated by that parameter and is skipped when
it is unset.
"""

import re
import uuid

import pytest

from tests.e2e.slurm.conftest import SUBMIT_USER, require_version

# The runtime partition the access test creates for its own matrix.
TEST_PARTITION = "q2"

# The stock partition that gets an AllowQOS whitelist pushed at runtime.
STOCK_PARTITION = "cpu"


def _uniq(prefix: str) -> str:
    """Unique name for this run, so tests never collide on the shared stack."""
    return f"e2e-access-{prefix}-{uuid.uuid4().hex[:10]}"


def _make_assoc(client, stack, acct: str, default_qos: str, qoslevel: list[str]) -> None:
    """Create the live account + account-level parent + cgray user assoc.

    The add_cond endpoint creates the account + its account-level (parent)
    association in one call; the plain create_associations endpoint adds the
    user-level assoc for the baked-in ``SUBMIT_USER`` with a default QOS and a
    granted QOS list (so explicit ``--qos`` is honored at submit).
    """
    client.create_accounts_with_associations(
        client.serialize_accounts_add_cond(accounts=[acct], clusters=[stack.cluster_name()])
    )
    client.create_associations(
        [
            client.serialize_association(
                account=acct,
                user=SUBMIT_USER,
                cluster=stack.cluster_name(),
                default_qos=default_qos,
                qoslevel=qoslevel,
            )
        ]
    )


def _submit_rc(stack, acct: str, partition: str, qos: str | None = None) -> tuple[int, str]:
    """Submit a ``sleep 1`` job as the baked-in user; return (submit rc, output).

    Runs inside slurmctld via ``runuser`` (the user must own a valid assoc).
    ``bash -c`` always exits 0, so the sbatch rc is captured with an echoed
    ``RC=$?`` marker (exec-in-container rc is not the sbatch rc).
    """
    qos_arg = f"--qos={qos} " if qos else ""
    out, _err, rc = stack.exec(
        "slurmctld",
        [
            "bash",
            "-c",
            f"cd /data && runuser -u {SUBMIT_USER} -- sbatch --partition={partition} "
            f"--account={acct} {qos_arg}--output=/dev/null --job-name=access "
            f"--wrap='sleep 1' 2>&1; echo RC=$?",
        ],
    )
    match = re.search(r"RC=(\d+)", out)
    return (int(match.group(1)) if match else -1), out


@pytest.fixture
def access_partition_config(slurm_stack, slurm_client):
    """Set up the access-control partition config for each test.

    Only versions that expose ``POST /partitions/`` can push AllowQOS at
    runtime, so the fixture skips the others (e.g. 25.11.x / v0.0.44).
    Function-scoped: the autouse ``slurm_cleanup`` wipes the runtime
    partition/QOS config after each test, so each test needs its own setup.
    """
    # Pushing AllowQOS via POST /partitions/ is a v0.0.45-only capability.
    require_version(slurm_stack, ">=26.05.4")

    # QOS lives in slurmdbd; persist there first. Some versions (v0.0.44) return
    # an empty body on success — treat absent/empty errors as success.
    body = slurm_client.upsert_qos([slurm_client.serialize_qos("cpu"), slurm_client.serialize_qos("q2")])
    assert not body.get("errors"), f"upsert_qos errors: {body.get('errors')}"
    # Load the new QOS into slurmctld's cache so partition allow_qos ids resolve.
    body = slurm_client.reconfigure()
    assert not body.get("errors"), f"reconfigure errors: {body.get('errors')}"
    # Push AllowQOS on cpu and create the runtime q2 partition in one call.
    body = slurm_client.update_partitions(
        [
            slurm_client.serialize_partition(STOCK_PARTITION, qos_allowed="cpu"),
            slurm_client.serialize_partition(TEST_PARTITION, qos_allowed="q2", nodes_configured="c1"),
        ]
    )
    assert not body.get("errors"), f"update_partitions errors: {body.get('errors')}"

    # Read back the pushed config so setup failures surface before the matrix.
    parts = slurm_client.get_partitions()
    by_name = {p.get("name"): p for p in parts.get("partitions", [])}
    assert by_name.get(STOCK_PARTITION, {}).get("qos", {}).get("allowed") == "cpu", by_name
    assert by_name.get(TEST_PARTITION, {}).get("qos", {}).get("allowed") == "q2", by_name

    yield


@pytest.mark.e2e
class TestPartitionAllowQosLive:
    """Partition AllowQOS whitelist enforced end-to-end on the live stack."""

    def test_allow_qos_whitelist_enforced_with_explicit_qos(self, slurm_stack, slurm_client, access_partition_config):
        """A partition accepts only jobs whose QOS is in its AllowQOS list."""
        acct = _uniq("acct")

        # Grant cgray both QOS so explicit --qos is honored, default to cpu.
        _make_assoc(slurm_client, slurm_stack, acct, "cpu", ["cpu", "q2"])

        # cpu partition: AllowQOS=cpu -> cpu accepted, q2 rejected.
        rc, out = _submit_rc(slurm_stack, acct, "cpu", qos="cpu")
        assert rc == 0, f"cpu + --qos=cpu should be allowed: {out!r}"
        rc, out = _submit_rc(slurm_stack, acct, "cpu", qos="q2")
        assert rc != 0, f"cpu + --qos=q2 should be denied: {out!r}"

        # q2 partition: AllowQOS=q2 -> q2 accepted, cpu rejected.
        rc, out = _submit_rc(slurm_stack, acct, TEST_PARTITION, qos="q2")
        assert rc == 0, f"q2 + --qos=q2 should be allowed: {out!r}"
        rc, out = _submit_rc(slurm_stack, acct, TEST_PARTITION, qos="cpu")
        assert rc != 0, f"q2 + --qos=cpu should be denied: {out!r}"

    def test_default_qos_gates_partition_access(self, slurm_stack, slurm_client, access_partition_config):
        """The association default QOS decides which partition a job may use."""
        # Scenario A: assoc default_qos=cpu -> cpu allowed, q2 denied.
        acct_a = _uniq("acctA")

        _make_assoc(slurm_client, slurm_stack, acct_a, "cpu", ["cpu", "q2"])
        rc, out = _submit_rc(slurm_stack, acct_a, STOCK_PARTITION)
        assert rc == 0, f"scenario A cpu (default_qos=cpu) should be allowed: {out!r}"
        rc, out = _submit_rc(slurm_stack, acct_a, TEST_PARTITION)
        assert rc != 0, f"scenario A q2 (default_qos=cpu) should be denied: {out!r}"

        # Scenario B: assoc default_qos=q2 -> q2 allowed, cpu denied.
        acct_b = _uniq("acctB")

        _make_assoc(slurm_client, slurm_stack, acct_b, "q2", ["cpu", "q2"])
        rc, out = _submit_rc(slurm_stack, acct_b, TEST_PARTITION)
        assert rc == 0, f"scenario B q2 (default_qos=q2) should be allowed: {out!r}"
        rc, out = _submit_rc(slurm_stack, acct_b, STOCK_PARTITION)
        assert rc != 0, f"scenario B cpu (default_qos=q2) should be denied: {out!r}"
