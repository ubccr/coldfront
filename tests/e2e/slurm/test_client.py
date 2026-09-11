# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live Slurm REST client CRUD round-trips.

Mirrors ``tests/slurm/test_client.py`` (the mocked endpoint classes) but talks
to a **real** slurmrestd/slurmdbd. Each test creates a uniquely-named entity,
reads it back through the client (verifying response parsing), then deletes it
so the shared session stack stays clean.

These are the integration-truth tests: any mismatch between what the mock
suite assumed and what the live API returns should be fixed here (the client
or the mock), per the mock-vs-e2e workflow in ``tests/e2e/README.md``.
"""

import uuid

import pytest

from coldfront.slurm.client.exceptions import (
    SlurmAssociationNotCreatedError,
    SlurmUserNotCreatedError,
)

# Cluster name defined in the slurm.conf (ClusterName=linux).
CLUSTER = "linux"


def _uniq(prefix: str) -> str:
    """Unique entity name for this run, so tests never collide on the shared stack."""
    return f"e2e-{prefix}-{uuid.uuid4().hex[:10]}"


def _account_payload(name: str, description: str = "e2e account") -> dict:
    """An account payload valid against the live ``account`` schema.

    slurmrestd requires ``description``, ``name`` and ``organization``.
    """
    return {"name": name, "description": description, "organization": "e2e"}


def _seed_account_with_assoc(slurm_client, acct: str) -> None:
    """Create an account **plus** its account-level (parent) association.

    Live stack behavior: plain ``create_accounts`` creates only the account
    record; the account-level association is what the hierarchy needs, and it
    is only created by the ``accounts_association`` add_cond endpoint.
    """
    body = slurm_client.create_accounts_with_associations(
        slurm_client.serialize_accounts_add_cond(accounts=[acct], clusters=[CLUSTER])
    )
    _assert_success(body)


def _seed_user(slurm_stack, slurm_client, acct: str, user: str) -> None:
    """Create a system user (uid) in the containers + a REST user record.

    slurmdbd requires the user to have a uid in /etc/passwd, else the REST
    user create silently no-ops. The REST ``create_users`` stores just the
    user record; the default account / associations come from the add_cond
    endpoints (see the live findings in this module's docstring).
    """
    slurm_stack.ensure_system_user(user)
    body = slurm_client.create_users([{"name": user, "default": {"account": acct, "wckey": ""}}])
    _assert_success(body)


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


def _assert_success(body: dict) -> None:
    """A successful API response must carry no errors.

    Some POST endpoints (e.g. ``users_association/``) return an empty body on
    success, so ``meta`` is not always present — only ``errors`` is reliable.
    """
    assert body.get("errors", []) == [], f"unexpected errors: {body.get('errors')}"


# ======================================================================
# ACCOUNTS
# ======================================================================


@pytest.mark.e2e
class TestAccountsLive:
    def test_create_get_delete_account(self, slurm_client):
        acct = _uniq("acct")

        # Create
        body = slurm_client.create_accounts([_account_payload(acct)])
        _assert_success(body)

        # Read back and verify parsing
        got = slurm_client.get_accounts(name=acct)
        _assert_success(got)
        accounts = got.get("accounts", [])
        names = {a.get("name", "") for a in accounts}
        assert acct in names

        # Delete
        del_body = slurm_client.delete_account(acct, CLUSTER)
        _assert_success(del_body)

        # Gone
        after = slurm_client.get_accounts(name=acct)
        assert acct not in {a.get("name", "") for a in after.get("accounts", [])}

    def test_delete_account_with_users_succeeds(self, slurm_stack, slurm_client):
        """Deleting an account that has a user+assoc succeeds on the live API.

        The live stack never enforces default-account protection: it deletes
        an account even while it is a user's default. There is no
        ``409``/``SlurmNoRemoveDefaultAccountError`` path on the supported
        stack, so that class and its mock were removed.
        """
        acct = _uniq("acct")
        user = _uniq("user")

        # account + account-level assoc + user + user-level assoc (add_cond path)
        _seed_account_with_assoc(slurm_client, acct)
        slurm_stack.ensure_system_user(user)
        body = slurm_client.create_users_with_associations(
            slurm_client.serialize_users_add_cond(
                users=[user], accounts=[acct], clusters=[CLUSTER], association={"fairshare": 1}
            )
        )
        _assert_success(body)

        # The account is still the user's default, yet the live API deletes it.
        del_body = slurm_client.delete_account(acct, CLUSTER)
        _assert_success(del_body)

        # user/assoc remain (account is gone); the autouse cleanup wipes them.
        got = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        _assert_success(got)
        assert not [a for a in got.get("associations", []) if a.get("account") == acct and a.get("user") == user]


# ======================================================================
# USERS
# ======================================================================


@pytest.mark.e2e
class TestUsersLive:
    def test_create_get_delete_user(self, slurm_stack, slurm_client):
        acct = _uniq("acct")
        user = _uniq("user")

        slurm_client.create_accounts([_account_payload(acct)])

        # uid in /etc/passwd is required or the REST user create silently no-ops
        body = slurm_client.create_users([{"name": user, "default": {"account": acct, "wckey": ""}}])
        _assert_success(body)

        got = slurm_client.get_users(name=user)
        _assert_success(got)
        users = got.get("users", [])
        names = {u.get("name", "") for u in users}
        assert user in names

        del_body = slurm_client.delete_user(user, CLUSTER)
        _assert_success(del_body)

        after = slurm_client.get_users(name=user)
        assert user not in {u.get("name", "") for u in after.get("users", [])}


# ======================================================================
# ASSOCIATIONS (access control)
# ======================================================================


@pytest.mark.e2e
class TestAssociationsLive:
    def test_create_get_delete_association(self, slurm_stack, slurm_client):
        acct = _uniq("acct")
        user = _uniq("user")

        # Hierarchy: account + account-level (parent) assoc, then user record.
        # Plain POST /associations/ cannot create the account-level assoc, so it
        # comes from the accounts_association add_cond endpoint.
        _seed_account_with_assoc(slurm_client, acct)
        _seed_user(slurm_stack, slurm_client, acct, user)

        # Plain user-level association works once the account-level parent exists.
        # Live plain POST /associations/ parses the nested assoc schema, so
        # fairshare is ``shares_raw`` here (``fairshare`` is silently ignored).
        assoc = {
            "account": acct,
            "user": user,
            "cluster": CLUSTER,
            "partition": "cpu",
            "shares_raw": 1,
        }
        body = slurm_client.create_associations([assoc])
        _assert_success(body)

        got = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        _assert_success(got)
        assocs = got.get("associations", [])
        matches = [
            a for a in assocs if a.get("account") == acct and a.get("user") == user and a.get("cluster") == CLUSTER
        ]
        assert matches, f"no association parsed for {acct}/{user}: {assocs}"

        del_body = slurm_client.delete_associations(acct, user, CLUSTER)
        _assert_success(del_body)

        after = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        assert not [a for a in after.get("associations", []) if a.get("account") == acct and a.get("user") == user]


# ======================================================================
# QOS
# ======================================================================


@pytest.mark.e2e
class TestQosLive:
    def test_upsert_and_get_qos(self, slurm_client):
        qos_name = _uniq("qos")

        body = slurm_client.upsert_qos([{"name": qos_name, "description": "e2e qos", "priority": 10}])
        _assert_success(body)

        got = slurm_client.get_qos(name=qos_name)
        _assert_success(got)
        qos_list = got.get("qos", [])
        assert any(q.get("name") == qos_name for q in qos_list)


# ======================================================================
# CONFIG (get / upsert)
# ======================================================================


@pytest.mark.e2e
class TestConfigLive:
    def test_get_config_parses_entities(self, slurm_client):
        config = slurm_client.get_config()
        _assert_success(config)
        # The config response should carry at least the cluster definitions.
        assert "clusters" in config, f"config response missing clusters: {list(config)}"
        cluster_names = {c.get("name", "") for c in config["clusters"]}
        assert CLUSTER in cluster_names, f"cluster {CLUSTER!r} not parsed: {config['clusters']}"

    def test_upsert_config_round_trip(self, slurm_client):
        """serialize_config -> upsert_config returns a clean accepted payload.

        Live stack behavior: POST /config does **not** create accounts/users/
        associations (it is an upsert that only touches existing entities), so
        this test only asserts the payload is accepted (no errors), not that it
        materialized anything.
        """
        payload = slurm_client.serialize_config(
            clusters=[{"name": CLUSTER, "control_type": "slurm"}],
            accounts=[_account_payload(_uniq("acct"), "e2e config")],
            users=[{"name": _uniq("user"), "default": {"account": _uniq("acct"), "wckey": ""}}],
            associations=[
                {
                    "account": _uniq("acct"),
                    "user": _uniq("user"),
                    "cluster": CLUSTER,
                    "partition": "cpu",
                }
            ],
        )
        body = slurm_client.upsert_config(payload)
        _assert_success(body)


# ======================================================================
# PARTITIONS / NODES (slurmctld reads)
# ======================================================================


@pytest.mark.e2e
class TestPartitionsNodesLive:
    def test_get_partitions_parses_name_field(self, slurm_stack, slurm_client):
        partitions = slurm_client.get_partitions()
        _assert_success(partitions)
        names = {p.get("name", "") for p in partitions.get("partitions", [])}
        assert "cpu" in names

    def test_get_nodes_parses(self, slurm_stack, slurm_client):
        nodes = slurm_client.get_nodes()
        _assert_success(nodes)
        node_names = {n.get("name", "") for n in nodes.get("nodes", [])}
        assert node_names, f"no nodes parsed: {nodes}"


# ======================================================================
# SILENT FAILURE (integration truth for the verification feature)
# ======================================================================


@pytest.mark.e2e
class TestSilentFailureLive:
    """The client must surface slurmdbd's silent no-ops as typed errors.

    These lock in the integration truth the verification feature was built
    for: a create that returns HTTP 200 / errors=[] but stores nothing must
    raise the typed ``*NotCreatedError``.
    """

    def test_create_user_with_missing_default_account_stores_record(self, slurm_client):
        """Plain create_users stores the user record even with a missing default account.

        The silent no-op lives at the **association** level, not the user-record
        level: slurmdbd records the user even with a non-existent default account
        and no OS uid. (The add_cond path is where a missing parent drops the
        user entirely — covered by ``test_create_users_with_associations_missing_parent_raises``.)
        """
        user = _uniq("user")
        ghost = _uniq("ghost-account")  # never created

        body = slurm_client.create_users([{"name": user, "default": {"account": ghost, "wckey": ""}}])
        _assert_success(body)

        # verification read-back: the user record materialized (no silent drop)
        assert user in {u.get("name", "") for u in slurm_client.get_users().get("users", [])}

    def test_create_association_missing_parent_raises(self, slurm_client):
        """A user-level association without its account-level parent is dropped."""
        acct = _uniq("acct")
        user = _uniq("user")

        # plain create_accounts stores only the account record, no parent assoc
        slurm_client.create_accounts([_account_payload(acct)])

        assoc = {
            "account": acct,
            "user": user,
            "cluster": CLUSTER,
        }
        with pytest.raises(SlurmAssociationNotCreatedError) as ei:
            slurm_client.create_associations([assoc])
        assert (acct, user, CLUSTER) in ei.value.missing

    def test_create_users_with_associations_missing_parent_raises(self, slurm_stack, slurm_client):
        """users_association with no account-level parent returns an empty body.

        The user has a real OS account (uid), but the account has no parent
        association, so the add_cond endpoint silently no-ops: empty body →
        read-back shows no association → typed error.
        """
        acct = _uniq("acct")
        user = _uniq("user")

        slurm_client.create_accounts([_account_payload(acct)])  # record only, no parent assoc
        slurm_stack.ensure_system_user(user)

        payload = slurm_client.serialize_users_add_cond(users=[user], accounts=[acct], clusters=[CLUSTER])
        with pytest.raises(SlurmUserNotCreatedError) as ei:
            slurm_client.create_users_with_associations(payload)
        assert user in ei.value.missing

    def test_create_accounts_with_associations_already_exists_no_raise(self, slurm_client):
        """Re-running accounts_association for an existing account is idempotent."""
        acct = _uniq("acct")

        # first run creates account + account-level assoc (added_accounts gate)
        slurm_client.create_accounts_with_associations(
            slurm_client.serialize_accounts_add_cond(accounts=[acct], clusters=[CLUSTER])
        )

        # second run: empty body (already exists) → read-back disambiguates → no raise
        body = slurm_client.create_accounts_with_associations(
            slurm_client.serialize_accounts_add_cond(accounts=[acct], clusters=[CLUSTER])
        )
        assert body.get("added_accounts") is None  # empty-body ambiguity
        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}


# ======================================================================
# USERS / ACCOUNTS WITH ASSOCIATIONS (bulk shortcuts)
# ======================================================================


@pytest.mark.e2e
class TestUsersAccountsAssocLive:
    def test_create_users_with_associations(self, slurm_stack, slurm_client):
        acct = _uniq("acct")
        user = _uniq("user")

        # users_association needs the account-level (parent) assoc to exist
        _seed_account_with_assoc(slurm_client, acct)
        slurm_stack.ensure_system_user(user)

        payload = slurm_client.serialize_users_add_cond(
            users=[user],
            accounts=[acct],
            clusters=[CLUSTER],
            partitions=["cpu"],
            association={"fairshare": 1},
        )
        body = slurm_client.create_users_with_associations(payload)
        _assert_success(body)

        # users_association creates the user-level association
        got = slurm_client.get_associations(account=acct, user=user, cluster=CLUSTER)
        assert any(a.get("account") == acct and a.get("user") == user for a in got.get("associations", []))

    def test_create_accounts_with_associations(self, slurm_client):
        acct = _uniq("acct")

        payload = slurm_client.serialize_accounts_add_cond(
            accounts=[acct],
            clusters=[CLUSTER],
            association={"fairshare": 1},
        )
        body = slurm_client.create_accounts_with_associations(payload)
        _assert_success(body)

        # accounts_association creates the account (account-level assoc), not a user assoc
        assert acct in {a.get("name", "") for a in slurm_client.get_accounts(name=acct).get("accounts", [])}
