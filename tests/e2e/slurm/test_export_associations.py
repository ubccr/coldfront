# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live e2e test: association dump export -> import into the real cluster.

Exercises the association flat-file dump path end to end:

* seed the Django models (baked-in system users as project members, ingested
  live cluster + QOS, active allocation + account + association),
* create the DB-only ``SlurmUser`` bookkeeping the dump looks up (the
  batch model's DB-only listener path),
* ``generate_association_dump`` -> write the dump to a file -> import it with
  ``sacctmgr -i load clean=account,qos``,
* verify the loaded live state matches the dump, then submit a real job as a
  project user to prove the imported associations actually work.
"""

import pytest

from coldfront.slurm.export import generate_association_dump
from coldfront.slurm.models import SlurmUser
from tests.e2e.slurm.conftest import submit_sleep_job, wait_for_job_completion
from tests.e2e.slurm.test_project_allocation import (
    SYSTEM_USERS,
    _seed_project_with_allocation,
)

# Cluster name defined in the vendored slurm.conf (ClusterName=linux).
CLUSTER = "linux"


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestAssociationDumpRoundTrip:
    """Association dump export -> live import -> job, round-trip."""

    def test_dump_load_round_trip_and_job(self, slurm_stack, slurm_client):
        """generate_association_dump loads via sacctmgr and reproduces live state."""
        cluster, account, allocation, _, users = _seed_project_with_allocation(slurm_client)
        acct = account.name

        # DB-only bookkeeping: create a SlurmUser row per project member (the
        # batch model's listener path). The dump looks these up.
        for name in SYSTEM_USERS:
            SlurmUser.objects.create(
                user=users[name],
                cluster=cluster,
                default_account=account,
            )

        # Generate the dump.
        dump = generate_association_dump(cluster)
        assert f"Cluster - '{CLUSTER}'" in dump
        assert f"Account - '{acct}'" in dump
        assert "User - 'csimmons'" in dump

        # Write the dump to a file and import it with sacctmgr. Plain load adds
        # the dump's accounts/users on top of the stack's origin state (the
        # stack is at origin at test start); the user lines carry the QOS the
        # activation pushed live, so submission still works.
        slurm_stack.exec("slurmctld", ["bash", "-c", f"cat > /tmp/assoc.dump <<'EOF'\n{dump}\nEOF"])
        out, err, rc = slurm_stack.exec(
            "slurmctld",
            ["bash", "-c", "sacctmgr -i load file=/tmp/assoc.dump"],
        )
        assert rc == 0, f"sacctmgr load failed (rc={rc}): {err.strip() or out.strip()}"

        # The loaded live state matches the dump: account parent + one user assoc
        # per project user.
        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        assert any(a.get("user") == "" for a in assocs), f"missing account-level parent: {assocs}"
        for name in SYSTEM_USERS:
            assert any(a.get("user") == name for a in assocs), f"{name} assoc missing: {assocs}"

        # A real job as a project user proves the imported assoc satisfies
        # AccountingStorageEnforce=associations.
        job_id = submit_sleep_job(slurm_stack, acct, seconds=30, username="csimmons")
        wait_for_job_completion(slurm_stack, job_id)
