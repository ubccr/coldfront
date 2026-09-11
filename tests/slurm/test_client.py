# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm REST API client.

Organized by test class:

- ``TestSerializers`` — pure Python, no HTTP mocking
- ``TestErrorMapping`` — pure Python, tests exception hierarchy
- ``TestRetryLogic`` — ``responses`` for transient failure sequences
- ``TestAccountEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestAssociationEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestUserEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestUserAssociationEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestConfigEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestPartitionEndpoints`` / ``TestJobUsageEndpoint`` — partition + usage queries

Version discovery, cross-version compatibility and OpenAPI spec conformance
live in ``test_versions.py``.
"""

import json
from unittest import mock

import pytest
import responses

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.exceptions import (
    SlurmAccountNotCreatedError,
    SlurmAssociationNotCreatedError,
    SlurmBadRequestError,
    SlurmError,
    SlurmNotCreatedError,
    SlurmUnavailableError,
    SlurmUserNotCreatedError,
)
from coldfront.slurm.client.versions import (
    api_version_for,
    supported_slurm_versions,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SAMPLE_ACCOUNT = {"name": "hpc-lab", "description": "Lab account", "organization": "University"}
_SAMPLE_ASSOCIATION = {
    "account": "hpc-lab",
    "user": "jsmith",
    "cluster": "hpc01",
    "partition": "gpu",
    "fairshare": 1,
    "defaultqos": "normal",
}
_SAMPLE_USER = {
    "name": "jsmith",
    "default": {"account": "hpc-lab", "wckey": ""},
}
# Default success response template — tests override with endpoint-specific data
_SUCCESS_RESPONSE = {
    "meta": {"plugin": {}, "client": {}, "slurm": {}},
    "errors": [],
    "warnings": [],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_BASE = "http://mock.slurm.test"
_DEFAULT_JWT = "test-token"
_DEFAULT_VER = supported_slurm_versions()[0]  # a supported Slurm release


def make_client(
    base_url: str = _DEFAULT_BASE,
    jwt_token: str = _DEFAULT_JWT,
    version: str = _DEFAULT_VER,
    **kwargs,
) -> SlurmClient:
    """Construct a SlurmClient with a fixed version (no discovery needed)."""
    return SlurmClient(
        base_url=base_url,
        jwt_token=jwt_token,
        version=version,
        **kwargs,
    )


def url_for(path_template: str, version: str = _DEFAULT_VER) -> str:
    """Build the full URL for a slurmdb or slurm path.

    ``version`` is a **Slurm release** (e.g. ``"25.11.8"``); the REST API
    version is resolved internally via :func:`api_version_for`.
    ``path_template`` is like ``"/associations/"`` (slurmdb) or ``"/jobs/"`` (slurm).
    Detects slurm vs slurmdb by path prefix.
    """
    api = api_version_for(version)
    if path_template.startswith("/slurm/"):
        return f"{_DEFAULT_BASE}/slurm/{api}/{path_template[len('/slurm/') :]}"
    return f"{_DEFAULT_BASE}/slurmdb/{api}/{path_template.lstrip('/')}"


def _assert_request_body(expected: dict) -> None:
    """Guard the wire format: the request body must match exactly.

    The mocked endpoint tests used to assert only the response, so a client
    could send the wrong body shape and still pass. The e2e suite caught that
    drift; every POST mock now asserts the exact request body too.

    Create endpoints may follow the POST with a verification GET, so find the
    request that actually carried a body (the POST) rather than the last call.
    """
    call = next(c for c in responses.calls if c.request.body)
    sent = json.loads(call.request.body)
    assert sent == expected, f"request body mismatch:\nsent={sent!r}\nwant={expected!r}"


# ======================================================================
# 1. SERIALIZER TESTS  (pure Python, no HTTP)
# ======================================================================


class TestSerializers:
    """Test that serializers produce correct dict structures.

    These are pure-data tests: no HTTP mocking needed. They verify
    field names, types, and conditional inclusion match the OpenAPI
    spec schemas.
    """

    def test_serialize_account_minimal(self):
        """Only ``name`` is required."""
        body = SlurmClient.serialize_account("test-acct")
        assert body == {"name": "test-acct"}

    def test_serialize_account_full(self):
        body = SlurmClient.serialize_account(
            "test-acct",
            description="My account",
            organization="Org",
        )
        assert body["name"] == "test-acct"
        assert body["description"] == "My account"
        assert body["organization"] == "Org"

    def test_serialize_association_required_only(self):
        body = SlurmClient.serialize_association("a", "u", "c")
        assert body == {"account": "a", "user": "u", "cluster": "c"}

    def test_serialize_association_full(self):
        """Every optional field lands in the nested wire format."""
        body = SlurmClient.serialize_association(
            "a",
            "u",
            "c",
            partition="gpu",
            fairshare=1,
            default_qos="normal",
            parent="root",
            max_jobs=10,
            max_submit_jobs=50,
            max_wall_duration_per_job=1440,
            max_tres_per_job={"node": 5},
            max_tres_mins_per_job={"cpu": 1000},
            grp_tres={"node": 20},
            grp_wall=43200,
            grp_tres_mins={"billing": 600000},
            qoslevel=["normal"],
        )
        assert body["partition"] == "gpu"
        assert body["shares_raw"] == 1
        assert body["default"] == {"qos": "normal"}
        assert body["parent_account"] == "root"
        assert body["qos"] == ["normal"]
        # Limits live under the nested ``max`` object (live assoc schema)
        assert body["max"]["jobs"]["active"] == 10
        assert body["max"]["jobs"]["total"] == 50
        assert body["max"]["jobs"]["per"]["wall_clock"] == 1440
        # TRES limits are tres_list arrays (live rejects dicts)
        assert body["max"]["tres"]["per"]["job"] == [{"type": "node", "count": 5}]
        assert body["max"]["tres"]["minutes"]["per"]["job"] == [{"type": "cpu", "count": 1000}]
        assert body["max"]["tres"]["total"] == [{"type": "node", "count": 20}]
        assert body["max"]["tres"]["group"]["minutes"] == [{"type": "billing", "count": 600000}]
        assert body["max"]["per"]["account"]["wall_clock"] == 43200

    def test_serialize_association_omits_unset(self):
        """Optional fields are omitted entirely when not provided."""
        body = SlurmClient.serialize_association("a", "u", "c")
        assert "grptresmins" not in body
        assert "max" not in body
        assert "qos" not in body

    def test_serialize_user_minimal(self):
        body = SlurmClient.serialize_user("jsmith", "hpc-lab")
        assert body["name"] == "jsmith"
        assert body["default"]["account"] == "hpc-lab"
        assert body["default"]["wckey"] == ""
        # default_qos not included
        assert "qos" not in body["default"]

    def test_serialize_user_full(self):
        body = SlurmClient.serialize_user("admin", "root", default_qos="normal", admin_level=2)
        assert body["default"]["qos"] == "normal"
        assert body["administrator_level"] == 2

    def test_serialize_kill_jobs_msg_minimal(self):
        body = SlurmClient.serialize_kill_jobs_msg()
        assert body == {"signal": "SIGTERM"}

    def test_serialize_kill_jobs_msg_full(self):
        body = SlurmClient.serialize_kill_jobs_msg(
            user_name="jsmith",
            account="hpc-lab",
            partition="gpu",
            signal="SIGKILL",
            job_state="RUNNING",
            job_name="test-job",
            user_id="1001",
            qos="normal",
            reservation="main",
            wckey="mykey",
            nodes="node[1-10]",
        )
        assert body["signal"] == "SIGKILL"
        assert body["user_name"] == "jsmith"
        assert body["account"] == "hpc-lab"
        assert body["partition"] == "gpu"
        assert body["job_state"] == "RUNNING"
        assert body["job_name"] == "test-job"
        assert body["user_id"] == "1001"
        assert body["qos"] == "normal"
        assert body["reservation"] == "main"
        assert body["wckey"] == "mykey"
        assert body["nodes"] == "node[1-10]"

    def test_serialize_users_add_cond_minimal(self):
        body = SlurmClient.serialize_users_add_cond(users=["jsmith"])
        assert body == {"association_condition": {"users": ["jsmith"]}}

    def test_serialize_users_add_cond_full(self):
        body = SlurmClient.serialize_users_add_cond(
            users=["jsmith", "bjones"],
            accounts=["hpc-lab"],
            clusters=["hpc01"],
            partitions=["gpu"],
            association={"fairshare": 1, "defaultqos": "normal"},
            wckeys=["mykey"],
        )
        cond = body["association_condition"]
        assert cond["users"] == ["jsmith", "bjones"]
        assert cond["accounts"] == ["hpc-lab"]
        assert cond["clusters"] == ["hpc01"]
        assert cond["partitions"] == ["gpu"]
        assert cond["association"]["fairshare"] == 1
        assert cond["wckeys"] == ["mykey"]
        # user_short carries the default account/wckey
        assert body["user"] == {"defaultaccount": "hpc-lab", "defaultwckey": "mykey"}

    # ------------------------------------------------------------------
    # Config serializers
    # ------------------------------------------------------------------

    def test_serialize_config_minimal(self):
        """No entity lists → empty body."""
        body = SlurmClient.serialize_config()
        assert body == {}

    def test_serialize_config_full(self):
        """Every entity list is included when provided."""
        body = SlurmClient.serialize_config(
            clusters=[{"name": "hpc01"}],
            accounts=[{"name": "hpc-lab"}],
            users=[{"name": "jsmith", "default": {"account": "hpc-lab", "wckey": ""}}],
            associations=[
                {
                    "account": "hpc-lab",
                    "user": "jsmith",
                    "cluster": "hpc01",
                    "partition": "gpu",
                    "fairshare": 1,
                }
            ],
            qos=[{"name": "normal"}],
            tres=[{"name": "node", "type": "cluster"}],
            wckeys=[{"name": "mykey"}],
        )
        assert body["accounts"] == [{"name": "hpc-lab"}]
        for key in ["clusters", "users", "associations", "qos", "tres", "wckeys"]:
            assert len(body[key]) == 1

    def test_serialize_accounts_add_cond_minimal(self):
        body = SlurmClient.serialize_accounts_add_cond(accounts=["hpc-lab"])
        assert body == {"association_condition": {"accounts": ["hpc-lab"]}}

    def test_serialize_accounts_add_cond_full(self):
        body = SlurmClient.serialize_accounts_add_cond(
            accounts=["hpc-lab"],
            clusters=["hpc01"],
            association={"fairshare": 1},
            description="Lab",
            organization="University",
        )
        cond = body["association_condition"]
        assert cond["accounts"] == ["hpc-lab"]
        assert cond["clusters"] == ["hpc01"]
        assert cond["association"]["fairshare"] == 1
        assert body["account"] == {"description": "Lab", "organization": "University"}

    def test_serializer_outputs_are_json_serializable(self):
        """All serializer outputs must pass through json.dumps without error."""
        import json

        cases = [
            SlurmClient.serialize_account("test"),
            SlurmClient.serialize_association("a", "u", "c", partition="gpu", fairshare=1),
            SlurmClient.serialize_user("u", "a", default_qos="q"),
            SlurmClient.serialize_kill_jobs_msg(user_name="u", account="a"),
            SlurmClient.serialize_users_add_cond(users=["u"]),
            SlurmClient.serialize_accounts_add_cond(accounts=["a"]),
        ]
        for c in cases:
            json.dumps(c)  # must not raise

    def test_serialize_qos(self):
        """serialize_qos nests limits under the qos_rec limits object; unset fields omitted."""
        body = SlurmClient.serialize_qos(
            name="normal",
            description="test",
            priority=10,
            limit_factor=0.5,
            max_submit_jobs_per_user=5,
            max_jobs_per_user=7,
            max_submit_jobs_per_account=6,
            max_jobs_per_account=8,
            max_wall_duration_per_job=120,
            grace_time=60,
        )
        assert body["name"] == "normal"
        assert body["description"] == "test"
        assert body["priority"] == 10
        limits = body["limits"]
        assert limits["grace_time"] == 60
        assert limits["factor"] == 0.5
        assert limits["max"]["jobs"]["per"]["user"] == 5
        assert limits["max"]["jobs"]["active_jobs"]["per"]["user"] == 7
        assert limits["max"]["jobs"]["per"]["account"] == 6
        assert limits["max"]["jobs"]["active_jobs"]["per"]["account"] == 8
        assert limits["max"]["wall_clock"]["per"]["job"] == 120

        # Unset limit fields are omitted entirely
        assert SlurmClient.serialize_qos("normal") == {"name": "normal"}


# ======================================================================
# 2. ERROR MAPPING TESTS  (pure Python, no HTTP)
# ======================================================================


class TestErrorMapping:
    """Test that error codes from the API are correctly mapped to exceptions.

    These tests exercise ``_raise_for_error`` logic without actual HTTP.
    """

    def _make_response(self, status: int, body: dict) -> mock.Mock:
        resp = mock.Mock()
        resp.status_code = status
        resp.content = json.dumps(body).encode()
        return resp

    @pytest.mark.parametrize("code", ["ESLURM_SOME_UNKNOWN_CODE", 42])
    def test_error_code_mapping(self, code):
        """Unknown/error_number codes fall back to the HTTP status mapping."""
        body = {"errors": [{"error": code, "description": "desc"}], "warnings": []}
        resp = self._make_response(400, body)
        client = make_client()
        with pytest.raises(SlurmBadRequestError):
            client._raise_for_error(resp, body)

    def test_known_code_raises_mapped_exception(self):
        """Known error codes map to their typed exception."""
        client = make_client()
        # ESLURM_DB_CONNECTION -> Unavailable
        with pytest.raises(SlurmUnavailableError):
            client._raise_for_error(
                self._make_response(503, {"errors": [{"error": "ESLURM_DB_CONNECTION"}], "warnings": []}),
                {"errors": [{"error": "ESLURM_DB_CONNECTION"}], "warnings": []},
            )
        # ESLURM_REST_INVALID_QUERY -> BadRequest
        with pytest.raises(SlurmBadRequestError):
            client._raise_for_error(
                self._make_response(400, {"errors": [{"error": "ESLURM_REST_INVALID_QUERY"}], "warnings": []}),
                {"errors": [{"error": "ESLURM_REST_INVALID_QUERY"}], "warnings": []},
            )

    def test_unknown_error_code_no_raise_on_200(self):
        """An unknown code on a 200 (no error status) is not an error."""
        body = {"errors": [{"error": "ESLURM_SOME_UNKNOWN_CODE", "description": "unknown"}], "warnings": []}
        resp = self._make_response(200, body)
        client = make_client()
        # Live stack emits soft no-ops like error_number=0/No error on 200s.
        client._raise_for_error(resp, body)

    def test_http_status_fallbacks(self):
        """Errors without a code, or a bare status, map to the HTTP fallback."""
        client = make_client()
        # 400 with string errors -> BadRequest
        with pytest.raises(SlurmBadRequestError):
            client._raise_for_error(
                self._make_response(400, {"errors": ["some error"]}),
                {"errors": ["some error"]},
            )
        # 503 with no errors -> Unavailable
        with pytest.raises(SlurmUnavailableError):
            client._raise_for_error(
                self._make_response(503, {"errors": [], "warnings": []}),
                {"errors": [], "warnings": []},
            )

    def test_no_error_paths(self):
        """200 responses, warnings, and empty errors never raise."""
        client = make_client()
        client._raise_for_error(
            self._make_response(200, {"errors": [], "warnings": [], "meta": {}}),
            {"errors": [], "warnings": [], "meta": {}},
        )
        client._raise_for_error(
            self._make_response(200, {"errors": [], "warnings": ["warn"]}),
            {"errors": [], "warnings": ["warn"]},
        )

    def test_exception_hierarchy(self):
        """The live-truth hierarchy: HTTP-mapped and verification classes."""
        exc = SlurmError("test", errors=["e1"], status_code=400)
        s = str(exc)
        assert "test" in s and "e1" in s and "400" in s
        assert issubclass(SlurmBadRequestError, SlurmError)
        assert issubclass(SlurmUnavailableError, SlurmError)
        assert issubclass(SlurmNotCreatedError, SlurmError)
        assert issubclass(SlurmUserNotCreatedError, SlurmNotCreatedError)
        assert issubclass(SlurmAccountNotCreatedError, SlurmNotCreatedError)
        assert issubclass(SlurmAssociationNotCreatedError, SlurmNotCreatedError)


# ======================================================================
# 4. RETRY LOGIC TESTS  (responses)
# ======================================================================


class TestRetryLogic:
    """Test that transient failures trigger retries with backoff.

    Uses ``responses`` to simulate sequences of 503 then 200.
    """

    @responses.activate
    def test_transient_503_retried_then_success(self):
        """First two calls return 503, third returns 200."""
        url = url_for("ping/")
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=200, json={"errors": [], "meta": {}})

        client = make_client(retries=3, retry_backoff=0.01)
        assert "meta" in client._request("GET", url)

    @responses.activate
    def test_transient_503_exhausted_retries(self):
        """All attempts return 503 — raises after retries are exhausted."""
        url = url_for("ping/")
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})

        client = make_client(retries=3, retry_backoff=0.01)
        with pytest.raises(SlurmUnavailableError):
            client._request("GET", url)

    @responses.activate
    def test_non_transient_error_not_retried(self):
        """A 400 error is raised immediately, not retried."""
        url = url_for("accounts/")
        responses.get(url, status=400, json={"errors": [{"error": "ESLURM_REST_INVALID_QUERY"}]})

        client = make_client(retries=3, retry_backoff=0.01)
        with pytest.raises(SlurmBadRequestError):
            client._request("GET", url)

    @responses.activate
    def test_network_failure_triggers_retry(self):
        """A connection error is retried, then raises SlurmUnavailableError."""
        url = url_for("ping/")
        client = make_client(retries=2, retry_backoff=0.01)
        with pytest.raises(SlurmUnavailableError):
            client._request("GET", url)


# ======================================================================
# 5. ACCOUNT ENDPOINT TESTS  (responses + spec)
# ======================================================================


class TestAccountEndpoints:
    """Test account create, query, and delete endpoints."""

    @responses.activate
    def test_create_accounts(self):
        """Live plain-create POST returns no data field (only errors/warnings/meta)."""
        url = url_for("accounts/")
        responses.post(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )
        # verification read-back carries the entity
        responses.get(url, status=200, json={"accounts": [_SAMPLE_ACCOUNT], **_SUCCESS_RESPONSE})

        client = make_client()
        result = client.create_accounts([_SAMPLE_ACCOUNT])
        # The POST response has no data field — entities come from the read-back
        assert "accounts" not in result
        assert result["errors"] == []
        _assert_request_body({"accounts": [_SAMPLE_ACCOUNT]})

    @responses.activate
    def test_create_accounts_verification(self):
        """Verification read-back decides success: missing entity raises, already
        present is idempotent success."""
        url = url_for("accounts/")
        responses.post(url, status=200, json={**_SUCCESS_RESPONSE})
        # read-back shows the account never materialized -> must raise
        responses.get(url, status=200, json={"accounts": [], **_SUCCESS_RESPONSE})

        client = make_client()
        with pytest.raises(SlurmAccountNotCreatedError) as ei:
            client.create_accounts([_SAMPLE_ACCOUNT])
        assert ei.value.missing == ["hpc-lab"]

        # read-back shows the account was already there -> idempotent success
        responses.post(url, status=200, json={**_SUCCESS_RESPONSE})
        responses.get(url, status=200, json={"accounts": [_SAMPLE_ACCOUNT], **_SUCCESS_RESPONSE})
        result = client.create_accounts([_SAMPLE_ACCOUNT])
        assert "accounts" not in result
        assert result["errors"] == []

    @responses.activate
    def test_delete_account(self):
        url = url_for("account/hpc-lab")
        responses.delete(url, status=200, json={**_SUCCESS_RESPONSE})
        client = make_client()
        result = client.delete_account("hpc-lab", "hpc01")
        assert result["errors"] == []
        assert responses.calls[0].request.params.get("cluster") == "hpc01"


# ======================================================================
# 6. ASSOCIATION ENDPOINT TESTS
# ======================================================================


class TestAssociationEndpoints:
    """Test association create, query, and delete endpoints."""

    @responses.activate
    def test_create_associations(self):
        """Live plain-create POST returns no data field (only errors/warnings/meta)."""
        url = url_for("associations/")
        responses.post(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )
        # verification read-back carries the entity
        responses.get(url, status=200, json={"associations": [_SAMPLE_ASSOCIATION], **_SUCCESS_RESPONSE})

        client = make_client()
        result = client.create_associations([_SAMPLE_ASSOCIATION])
        assert "associations" not in result
        assert result["errors"] == []
        _assert_request_body({"associations": [_SAMPLE_ASSOCIATION]})

    @responses.activate
    def test_create_associations_silent_noop_raises(self):
        """POST succeeds but the association never stored — must raise.

        This is the live behavior when the parent account-level association is
        missing (or the user has no uid): slurmdbd silently drops the write.
        """
        url = url_for("associations/")
        responses.post(url, status=200, json={**_SUCCESS_RESPONSE})
        # read-back shows no associations at all
        responses.get(url, status=200, json={"associations": [], **_SUCCESS_RESPONSE})

        client = make_client()
        with pytest.raises(SlurmAssociationNotCreatedError) as ei:
            client.create_associations([_SAMPLE_ASSOCIATION])
        assert ei.value.missing == [("hpc-lab", "jsmith", "hpc01")]
        _assert_request_body({"associations": [_SAMPLE_ASSOCIATION]})


# ======================================================================
# 7. USER ENDPOINT TESTS
# ======================================================================


class TestUserEndpoints:
    """Test user create, query, and delete endpoints."""

    @responses.activate
    def test_create_users(self):
        """Live plain-create POST returns no data field (only errors/warnings/meta)."""
        url = url_for("users/")
        responses.post(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )
        # verification read-back carries the entity
        responses.get(url, status=200, json={"users": [_SAMPLE_USER], **_SUCCESS_RESPONSE})

        client = make_client()
        result = client.create_users([_SAMPLE_USER])
        assert "users" not in result
        assert result["errors"] == []
        _assert_request_body({"users": [_SAMPLE_USER]})

    @responses.activate
    def test_create_users_silent_noop_raises(self):
        """POST succeeds but the user never stored — must raise.

        This is the live behavior when the user's default account does not
        exist, or the user has no uid in /etc/passwd.
        """
        url = url_for("users/")
        responses.post(url, status=200, json={**_SUCCESS_RESPONSE})
        responses.get(url, status=200, json={"users": [], **_SUCCESS_RESPONSE})

        client = make_client()
        with pytest.raises(SlurmUserNotCreatedError) as ei:
            client.create_users([_SAMPLE_USER])
        assert ei.value.missing == ["jsmith"]
        _assert_request_body({"users": [_SAMPLE_USER]})


# ======================================================================
# 7b. QOS ENDPOINT TESTS
# ======================================================================


class TestQosEndpoints:
    """Test QOS create/query/delete endpoints."""

    @responses.activate
    def test_upsert_qos(self):
        """Live upsert_qos POST returns no data field (only errors/warnings/meta)."""
        url = url_for("qos/")
        qos = {"name": "normal", "priority": 10}
        responses.post(
            url,
            status=200,
            json={**_SUCCESS_RESPONSE},
        )

        client = make_client()
        result = client.upsert_qos([qos])
        assert "qos" not in result
        assert result["errors"] == []
        _assert_request_body({"qos": [qos]})

    @responses.activate
    def test_delete_qos(self):
        url = url_for("qos/normal")
        responses.delete(url, status=200, json={**_SUCCESS_RESPONSE})
        client = make_client()
        result = client.delete_qos("normal")
        assert result["errors"] == []


class TestUserAssociationEndpoints:
    """Test bulk user+association and account+association endpoints."""

    @responses.activate
    def test_create_users_with_associations(self):
        url = url_for("users_association/")
        body = {
            "association_condition": {
                "users": ["jsmith"],
                "accounts": ["hpc-lab"],
                "clusters": ["hpc01"],
                "association": {"fairshare": 1},
            },
            "user": {"defaultaccount": "hpc-lab"},
        }
        responses.post(
            url,
            status=200,
            json={
                "added_users": " Adding User(s)\n  jsmith\n",
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_users_with_associations(body)
        assert result["added_users"]
        _assert_request_body(body)
        # gate present → no verification GET issued
        assert len(responses.calls) == 1

    @responses.activate
    def test_create_users_with_associations_verification(self):
        """Empty body on users_association: missing user raises, existing is idempotent."""
        url = url_for("users_association/")
        body = {
            "association_condition": {"users": ["jsmith"], "accounts": ["hpc-lab"], "clusters": ["hpc01"]},
            "user": {"defaultaccount": "hpc-lab"},
        }
        # live silent-failure response is a completely empty body (no keys)
        responses.post(url, status=200, json={})
        # read-back shows the user gained no association -> must raise
        responses.get(url_for("associations/"), status=200, json={"associations": [], **_SUCCESS_RESPONSE})

        client = make_client()
        with pytest.raises(SlurmUserNotCreatedError) as ei:
            client.create_users_with_associations(body)
        assert ei.value.missing == ["jsmith"]

        # read-back shows the user's association already exists -> idempotent
        responses.post(url, status=200, json={})
        responses.get(
            url_for("associations/"), status=200, json={"associations": [_SAMPLE_ASSOCIATION], **_SUCCESS_RESPONSE}
        )
        assert client.create_users_with_associations(body) == {}

    @responses.activate
    def test_create_accounts_with_associations(self):
        url = url_for("accounts_association/")
        body = {
            "association_condition": {
                "accounts": ["hpc-lab"],
                "clusters": ["hpc01"],
                "association": {"fairshare": 1},
            }
        }
        responses.post(
            url,
            status=200,
            json={
                "added_accounts": " Adding Account(s)\n  hpc-lab\n",
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_accounts_with_associations(body)
        assert result["added_accounts"]
        _assert_request_body(body)
        # gate present → no verification GET issued
        assert len(responses.calls) == 1

    @responses.activate
    def test_create_accounts_with_associations_verification(self):
        """Empty body on accounts_association: missing account raises, existing is idempotent."""
        url = url_for("accounts_association/")
        body = {
            "association_condition": {"accounts": ["hpc-lab"], "clusters": ["hpc01"]},
        }
        responses.post(url, status=200, json={})
        responses.get(url_for("accounts/"), status=200, json={"accounts": [], **_SUCCESS_RESPONSE})

        client = make_client()
        with pytest.raises(SlurmAccountNotCreatedError) as ei:
            client.create_accounts_with_associations(body)
        assert ei.value.missing == ["hpc-lab"]

        responses.post(url, status=200, json={})
        responses.get(url_for("accounts/"), status=200, json={"accounts": [_SAMPLE_ACCOUNT], **_SUCCESS_RESPONSE})
        assert client.create_accounts_with_associations(body) == {}


# ======================================================================
# 9. CONFIG ENDPOINT TESTS
# ======================================================================


class TestPartitionEndpoints:
    """Test partition query/update endpoints (slurmctld)."""

    @responses.activate
    def test_update_partitions(self):
        url = url_for("/slurm/partitions/")
        responses.post(url, status=200, json={**_SUCCESS_RESPONSE})
        client = make_client()
        result = client.update_partitions([{"name": "gpu", "allow_qos": ["normal"]}])
        assert result["errors"] == []
        _assert_request_body({"partitions": [{"name": "gpu", "allow_qos": ["normal"]}]})


class TestJobUsageEndpoint:
    """Test the get_job_usage REST query (usage window)."""

    @responses.activate
    def test_queries_jobs_with_overlap_window(self):
        resp_body = {
            "jobs": [
                {
                    "account": "acct-a",
                    "partition": "gpu",
                    "qos": "normal",
                    "time": {"start": 1000, "end": 5000},
                    "tres": {
                        "allocated": [
                            {"type": "billing", "name": "billing", "id": 5, "count": 2},
                            {"type": "node", "name": "node", "id": 4, "count": 4},
                        ]
                    },
                }
            ],
            "errors": [],
            "warnings": [],
        }
        responses.add(
            responses.GET,
            f"{_DEFAULT_BASE}/slurmdb/{api_version_for(_DEFAULT_VER)}/jobs/",
            json=resp_body,
            status=200,
        )
        client = make_client()
        jobs = client.get_job_usage(86400, 172800, "hpc01")

        req = responses.calls[0].request
        assert req.params["start_time"] == "86400"
        assert req.params["end_time"] == "172800"
        assert req.params["cluster"] == "hpc01"
        assert req.params["disable_truncate_usage_time"] == "true"
        assert jobs[0]["account"] == "acct-a"
        assert jobs[0]["tres"]["allocated"][0]["count"] == 2

        # empty response -> []
        responses.add(
            responses.GET,
            f"{_DEFAULT_BASE}/slurmdb/{api_version_for(_DEFAULT_VER)}/jobs/",
            json={"jobs": [], "errors": [], "warnings": []},
            status=200,
        )
        assert client.get_job_usage(86400, 172800, "hpc01") == []


class TestConfigEndpoints:
    """Test config upsert and error handling (wire-format guards).

    Plain config GET/dump round-trips are covered by the live e2e suite; the
    mock keeps the serialized-config wire guard and the 422 error path.
    """

    @responses.activate
    def test_upsert_config(self):
        url = url_for("config")
        responses.post(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        config = SlurmClient.serialize_config(
            accounts=[{"name": "hpc-lab"}],
            users=[
                {
                    "name": "jsmith",
                    "default": {"account": "hpc-lab", "wckey": ""},
                }
            ],
            associations=[
                {
                    "account": "hpc-lab",
                    "user": "jsmith",
                    "cluster": "hpc01",
                    "partition": "gpu",
                    "fairshare": 1,
                }
            ],
        )

        client = make_client()
        result = client.upsert_config(config)
        assert "errors" in result
        assert result["errors"] == []
        assert "warnings" in result
        assert result["warnings"] == []

    @responses.activate
    def test_upsert_config_error(self):
        """Test error handling when upsert fails."""
        url = url_for("config")
        responses.post(
            url,
            status=400,
            json={
                "errors": ["ESLURM_REST_INVALID_QUERY: Bad request"],
                "warnings": [],
                "meta": {},
            },
        )

        config = SlurmClient.serialize_config(
            accounts=[{"name": ""}],  # invalid empty name
        )

        client = make_client()
        with pytest.raises(SlurmBadRequestError):
            client.upsert_config(config)
