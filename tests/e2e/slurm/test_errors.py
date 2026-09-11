# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live Slurm REST error-path contract tests.

These settle what the live slurmrestd/slurmdbd actually returns on error
paths, and correct any mock assumptions that don't match. Findings locked in
here (26.05.4 -> v0.0.45 and 25.11.8 -> v0.0.44):

* Re-creating an already-existing account is **silent success** (errors=[]),
  not a 409 ``ESLURM_ALREADY_DB_ENTRY``. There is no ``409`` path on the
  supported stack, so the ``*_with_conflict_ok`` wrappers and the 409
  already-exists classes/mocks were **removed**.
* Deleting a nonexistent user / account / association is **silent success**
  (empty body), not a 404 ``ESLURM_USER_ID_MISSING``. There is no ``404``
  path on the supported stack, so the not-found classes/mocks were removed.
* A malformed payload returns **422** -> ``SlurmBadRequestError``.
* An invalid JWT returns **502** -> ``SlurmUnavailableError`` (retried), and a
  *valid-but-non-admin* JWT also returns 502 — auth failures always surface
  as db-connection unavailability on this stack. No ``403`` auth path exists,
  so ``SlurmAuthError`` was removed.
* ``kill_job`` on a nonexistent job is **silent success** (no invalid-job error).
* ``get_job_usage`` in a window with no jobs returns **[]** and parses cleanly.

Per the mock-vs-e2e workflow in ``tests/e2e/README.md``: there is one reality
(the supported slurmrestd versions), and the mock suite replays it. The
contract tests here are the integration-truth; the mock suite mirrors the same
live response shapes (e.g. plain-create POSTs carry no data field).

:class:`TestIdempotentUpsertLive` locks the "re-run fills only gaps"
idempotency the ColdFront sync re-run path relies on: re-creating entities
and re-running the add_cond shortcuts are all silent-success / present-counts-
as-success, so a re-run never raises.
"""

import time
import uuid

import pytest

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.exceptions import (
    SlurmBadRequestError,
    SlurmUnavailableError,
)

# Cluster name defined in the slurm.conf (ClusterName=linux).
CLUSTER = "linux"


def _uniq(prefix: str) -> str:
    """Unique entity name for this run, so tests never collide on the shared stack."""
    return f"e2e-{prefix}-{uuid.uuid4().hex[:10]}"


def _assert_success(body: dict) -> None:
    """A successful API response must carry no errors."""
    assert body.get("errors", []) == [], f"unexpected errors: {body.get('errors')}"


@pytest.mark.e2e
class TestErrorContractLive:
    """Settle the error-path contract against the live stack."""

    def test_recreate_account_is_silent_success(self, slurm_client):
        """Re-creating an existing account does not raise already-exists."""
        acct = _uniq("acct")

        payload = {"name": acct, "description": "d", "organization": "o"}
        first = slurm_client.create_accounts([payload])
        _assert_success(first)

        # Live stack returns errors=[] (no 409) — the conflict_ok wrapper and
        # the 409 already-exists mock are pure-logic, not integration-truth.
        second = slurm_client.create_accounts([payload])
        _assert_success(second)

        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}

    def test_delete_nonexistent_user_silent_success(self, slurm_client):
        """Deleting a nonexistent user returns an empty success body, not 404."""
        body = slurm_client.delete_user(_uniq("ghost-user"), CLUSTER)
        assert body.get("errors", []) == []

    def test_delete_nonexistent_account_silent_success(self, slurm_client):
        """Deleting a nonexistent account returns an empty success body, not 404."""
        body = slurm_client.delete_account(_uniq("ghost-acct"), CLUSTER)
        assert body.get("errors", []) == []

    def test_delete_nonexistent_association_silent_success(self, slurm_client):
        """Deleting a nonexistent association returns an empty success body."""
        body = slurm_client.delete_associations(_uniq("ghost-acct"), _uniq("ghost-user"), CLUSTER)
        assert body.get("errors", []) == []

    def test_invalid_payload_raises_bad_request(self, slurm_client):
        """A payload missing required fields returns 422 -> SlurmBadRequestError."""
        acct = _uniq("acct")
        # account schema requires description + organization
        with pytest.raises(SlurmBadRequestError) as ei:
            slurm_client.create_accounts([{"name": acct}])
        assert ei.value.status_code == 422

    def test_invalid_jwt_raises_unavailable(self, slurm_client):
        """An invalid JWT surfaces as 502 -> SlurmUnavailableError, not auth.

        slurmrestd cannot authenticate the caller, so it fails to open the
        slurmdbd connection and returns 502 (retried). A *valid-but-non-admin*
        JWT also returns 502 (verified live via ``scontrol token username=``),
        so there is no 403 auth path on this stack and ``SlurmAuthError`` was
        removed. The exact status surfaced (502 from the API vs the client's
        503 fallback after retries) is a retry-config artifact — the contract
        is the error type.
        """
        bad = SlurmClient(
            base_url=slurm_client.base_url,
            jwt_token="invalid-token",
            version=slurm_client.version,
            retries=0,  # fail fast; the 502 is deterministic
        )
        with pytest.raises(SlurmUnavailableError):
            bad.get_config()

    def test_kill_job_nonexistent_silent_success(self, slurm_client):
        """Killing a nonexistent job returns success (no invalid-job error)."""
        body = slurm_client.kill_job("999999")
        assert body.get("errors", []) == []

    def test_get_job_usage_empty_parses(self, slurm_client):
        """A window with no jobs returns [] and parses cleanly.

        Uses a **future** window (no completed job can fall there), so the
        assertion stays order-independent even though the usage tests
        submit real jobs to the shared session-scoped stock stack.
        """
        now = int(time.time())
        body = slurm_client.get_job_usage(start_time=now + 3600, end_time=now + 7200, cluster=CLUSTER)
        assert body == []


def _seed_account_with_assoc(slurm_client, acct: str) -> None:
    """Create an account plus its account-level (parent) association."""
    body = slurm_client.create_accounts_with_associations(
        slurm_client.serialize_accounts_add_cond(accounts=[acct], clusters=[CLUSTER])
    )
    _assert_success(body)


@pytest.mark.e2e
class TestIdempotentUpsertLive:
    """Lock the "re-run fills only gaps" idempotency the sync re-run path relies on.

    Live findings: re-creating an entity (account / association) is silent
    success, and the verification read-back counts an already-present entity as
    success. Re-running an add_cond shortcut returns an empty body that the
    read-back disambiguates to "already present". So re-running a whole sync
    sequence never raises and fills only the gaps.
    """

    def test_full_sync_sequence_re_run(self, slurm_stack, slurm_client):
        """Re-running the whole account+parent+user+assoc sequence is idempotent.

        Models the ColdFront sync re-run: an admin fixes an OS account and
        re-runs sync; every create is a silent success / present-counts-as-
        success, so nothing raises and no gaps remain.
        """
        acct = _uniq("acct")
        user = _uniq("user")

        account_payload = {"name": acct, "description": "d", "organization": "o"}
        assoc_payload = {
            "account": acct,
            "user": user,
            "cluster": CLUSTER,
            "partition": "cpu",
            "fairshare": 1,
        }

        def run_sequence() -> None:
            slurm_client.create_accounts([account_payload])  # account record
            _seed_account_with_assoc(slurm_client, acct)  # account-level parent
            slurm_stack.ensure_system_user(user)
            slurm_client.create_users([{"name": user, "default": {"account": acct, "wckey": ""}}])
            slurm_client.create_associations([assoc_payload])  # user-level assoc

        run_sequence()
        # Re-run the entire sequence — all re-creates are silent success.
        run_sequence()

        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}
        got = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        assert any(a.get("account") == acct and a.get("user") == user for a in got.get("associations", []))

    def test_partial_upsert_fills_gaps(self, slurm_stack, slurm_client):
        """Re-running with a new user fills only the missing gap; existing stays."""
        acct = _uniq("acct")
        user1 = _uniq("user")
        user2 = _uniq("user")

        # First run: account + parent + user1 + user1 assoc
        account_payload = {"name": acct, "description": "d", "organization": "o"}
        slurm_client.create_accounts([account_payload])
        _seed_account_with_assoc(slurm_client, acct)
        slurm_stack.ensure_system_user(user1)
        slurm_client.create_users([{"name": user1, "default": {"account": acct, "wckey": ""}}])
        slurm_client.create_associations([{"account": acct, "user": user1, "cluster": CLUSTER, "partition": "cpu"}])

        # Re-run with user2 added — the existing account/user1 stay, user2 fills the gap.
        slurm_stack.ensure_system_user(user2)
        slurm_client.create_accounts([account_payload])  # silent success
        slurm_client.create_users([{"name": user2, "default": {"account": acct, "wckey": ""}}])
        slurm_client.create_associations([{"account": acct, "user": user2, "cluster": CLUSTER, "partition": "cpu"}])

        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        users_present = {a.get("user", "") for a in assocs if a.get("account") == acct}
        assert user1 in users_present
        assert user2 in users_present

    def test_association_recreate_silent_success(self, slurm_stack, slurm_client):
        """Re-creating an existing user-level association is silent success."""
        acct = _uniq("acct")
        user = _uniq("user")

        _seed_account_with_assoc(slurm_client, acct)
        slurm_stack.ensure_system_user(user)
        slurm_client.create_users([{"name": user, "default": {"account": acct, "wckey": ""}}])
        assoc = {"account": acct, "user": user, "cluster": CLUSTER, "partition": "cpu"}

        slurm_client.create_associations([assoc])
        second = slurm_client.create_associations([assoc])
        _assert_success(second)  # errors=[] — no 409 already-exists

    def test_users_association_rerun_idempotent(self, slurm_stack, slurm_client):
        """Re-running users_association for an existing user+assoc is idempotent.

        First run returns the ``added_users`` gate; the re-run returns an empty
        body, which the read-back disambiguates to "already present" -> no raise.
        """
        acct = _uniq("acct")
        user = _uniq("user")

        _seed_account_with_assoc(slurm_client, acct)
        slurm_stack.ensure_system_user(user)
        payload = slurm_client.serialize_users_add_cond(users=[user], accounts=[acct], clusters=[CLUSTER])

        first = slurm_client.create_users_with_associations(payload)
        assert first.get("added_users")  # gate present on fresh add

        second = slurm_client.create_users_with_associations(payload)
        assert second.get("added_users") is None  # empty-body ambiguity
        # read-back disambiguated: the association is already present, no raise
        got = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        assert any(a.get("account") == acct and a.get("user") == user for a in got.get("associations", []))
