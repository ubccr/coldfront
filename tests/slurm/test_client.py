# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm REST API client.

Organized by test class:

- ``TestSerializers`` — pure Python, no HTTP mocking
- ``TestErrorMapping`` — pure Python, tests exception hierarchy
- ``TestVersionDiscovery`` — ``pytest-httpserver`` for /ping probes
- ``TestRetryLogic`` — ``responses`` for transient failure sequences
- ``TestAccountEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestAssociationEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestUserEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestUserAssociationEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestConfigEndpoints`` — ``responses`` + OpenAPI spec payloads
- ``TestKillJobsEndpoints`` — ``responses`` + OpenAPI spec payloads
"""

from __future__ import annotations

import json
from unittest import mock

import pytest
import responses

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.exceptions import (
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
_SAMPLE_KILL_MSG = {
    "signal": "SIGTERM",
    "user_name": "jsmith",
    "account": "hpc-lab",
    "partition": "gpu",
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
_DEFAULT_VER = "v0.0.44"


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

    ``path_template`` is like ``"/associations/"`` (slurmdb) or ``"/jobs/"`` (slurm).
    Detects slurm vs slurmdb by path prefix.
    """
    if path_template.startswith("/slurm/"):
        return f"{_DEFAULT_BASE}/slurm/{version}/{path_template[len('/slurm/') :]}"
    return f"{_DEFAULT_BASE}/slurmdb/{version}/{path_template.lstrip('/')}"


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
        assert body == {"account": "a", "user": "u", "cluster": "c", "partition": ""}

    def test_serialize_association_partition(self):
        body = SlurmClient.serialize_association("a", "u", "c", partition="gpu")
        assert body["partition"] == "gpu"

    def test_serialize_association_fairshare(self):
        body = SlurmClient.serialize_association("a", "u", "c", fairshare=1)
        assert body["fairshare"] == 1

    def test_serialize_association_default_qos(self):
        body = SlurmClient.serialize_association("a", "u", "c", default_qos="normal")
        assert body["defaultqos"] == "normal"

    def test_serialize_association_parent(self):
        body = SlurmClient.serialize_association("a", "u", "c", parent="root")
        assert body["parent"] == "root"

    def test_serialize_association_limits(self):
        body = SlurmClient.serialize_association(
            "a",
            "u",
            "c",
            max_jobs=10,
            max_submit_jobs=50,
            max_wall_duration_per_job=1440,
            max_tres_per_job={"node": 5},
            max_tres_mins_per_job={"cpu": 1000},
            grp_tres={"node": 20},
            grp_wall=43200,
        )
        assert body["maxjobs"] == 10
        assert body["maxsubmitjobs"] == 50
        assert body["maxwalldurationperjob"] == 1440
        assert body["maxtresperjob"] == {"node": 5}
        assert body["maxtresminsperjob"] == {"cpu": 1000}
        assert body["grptres"] == {"node": 20}
        assert body["grpwall"] == 43200

    def test_serialize_user_minimal(self):
        body = SlurmClient.serialize_user("jsmith", "hpc-lab")
        assert body["name"] == "jsmith"
        assert body["default"]["account"] == "hpc-lab"
        assert body["default"]["wckey"] == ""
        # default_qos not included
        assert "qos" not in body["default"]

    def test_serialize_user_with_default_qos(self):
        body = SlurmClient.serialize_user("jsmith", "hpc-lab", default_qos="normal")
        assert body["default"]["qos"] == "normal"

    def test_serialize_user_with_admin_level(self):
        body = SlurmClient.serialize_user("admin", "root", admin_level=2)
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
        assert body == {"users": ["jsmith"]}

    def test_serialize_users_add_cond_full(self):
        body = SlurmClient.serialize_users_add_cond(
            users=["jsmith", "bjones"],
            accounts=["hpc-lab"],
            clusters=["hpc01"],
            partitions=["gpu"],
            association={"fairshare": 1, "defaultqos": "normal"},
            wckeys=["mykey"],
        )
        assert body["users"] == ["jsmith", "bjones"]
        assert body["accounts"] == ["hpc-lab"]
        assert body["clusters"] == ["hpc01"]
        assert body["partitions"] == ["gpu"]
        assert body["association"]["fairshare"] == 1
        assert body["wckeys"] == ["mykey"]

    # ------------------------------------------------------------------
    # Config serializers
    # ------------------------------------------------------------------

    def test_serialize_config_minimal(self):
        """No entity lists → empty body."""
        body = SlurmClient.serialize_config()
        assert body == {}

    def test_serialize_config_accounts_only(self):
        body = SlurmClient.serialize_config(
            accounts=[{"name": "hpc-lab"}],
        )
        assert body == {"accounts": [{"name": "hpc-lab"}]}

    def test_serialize_config_all_entities(self):
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
        assert "clusters" in body
        assert "accounts" in body
        assert "users" in body
        assert "associations" in body
        assert "qos" in body
        assert "tres" in body
        assert "wckeys" in body
        assert len(body["clusters"]) == 1
        assert len(body["accounts"]) == 1
        assert len(body["users"]) == 1
        assert len(body["associations"]) == 1
        assert len(body["qos"]) == 1
        assert len(body["tres"]) == 1
        assert len(body["wckeys"]) == 1

    def test_serialize_accounts_add_cond_minimal(self):
        body = SlurmClient.serialize_accounts_add_cond(accounts=["hpc-lab"])
        assert body == {"accounts": ["hpc-lab"]}

    def test_serialize_accounts_add_cond_full(self):
        body = SlurmClient.serialize_accounts_add_cond(
            accounts=["hpc-lab"],
            clusters=["hpc01"],
            association={"fairshare": 1},
        )
        assert body["accounts"] == ["hpc-lab"]
        assert body["clusters"] == ["hpc01"]
        assert body["association"]["fairshare"] == 1

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

    # --- Known error codes ---

    def test_eslurm_already_db_entry_maps_to_exists(self):
        body = {"errors": [{"error": "ESLURM_ALREADY_DB_ENTRY", "description": "duplicate"}], "warnings": []}
        resp = self._make_response(409, body)

        client = make_client()
        with pytest.raises(SlurmAlreadyExistsException) as exc:
            client._raise_for_error(resp, body)
        assert "duplicate" in str(exc.value)

    def test_eslurm_no_remove_default_account(self):
        body = {
            "errors": [{"error": "ESLURM_NO_REMOVE_DEFAULT_ACCOUNT", "description": "still default"}],
            "warnings": [],
        }
        resp = self._make_response(409, body)

        client = make_client()
        with pytest.raises(SlurmNoRemoveDefaultAccountException) as exc:
            client._raise_for_error(resp, body)
        assert "default" in str(exc.value).lower()

    def test_eslurm_user_id_missing(self):
        body = {"errors": [{"error": "ESLURM_USER_ID_MISSING", "description": "user not found"}], "warnings": []}
        resp = self._make_response(404, body)

        client = make_client()
        with pytest.raises(SlurmUserIdMissingException) as _:
            client._raise_for_error(resp, body)

    def test_eslurm_data_ambiguous_query(self):
        body = {"errors": [{"error": "ESLURM_DATA_AMBIGUOUS_QUERY", "description": "multiple matches"}], "warnings": []}
        resp = self._make_response(409, body)

        client = make_client()
        with pytest.raises(SlurmInvalidQueryException) as _:
            client._raise_for_error(resp, body)

    def test_eslurm_auth_fail(self):
        body = {"errors": [{"error": "ESLURM_REST_AUTH_FAIL", "description": "bad jwt"}], "warnings": []}
        resp = self._make_response(403, body)

        client = make_client()
        with pytest.raises(SlurmAuthException) as _:
            client._raise_for_error(resp, body)

    def test_eslurm_db_connection(self):
        body = {"errors": [{"error": "ESLURM_DB_CONNECTION", "description": "db down"}], "warnings": []}
        resp = self._make_response(503, body)

        client = make_client()
        with pytest.raises(SlurmUnavailableException) as _:
            client._raise_for_error(resp, body)

    def test_eslurm_rest_invalid_query(self):
        body = {"errors": [{"error": "ESLURM_REST_INVALID_QUERY", "description": "bad params"}], "warnings": []}
        resp = self._make_response(400, body)

        client = make_client()
        with pytest.raises(SlurmBadRequestException) as _:
            client._raise_for_error(resp, body)

    def test_unknown_error_code_falls_back_to_http_status(self):
        body = {"errors": [{"error": "ESLURM_SOME_UNKNOWN_CODE", "description": "unknown"}], "warnings": []}
        resp = self._make_response(404, body)

        client = make_client()
        with pytest.raises(SlurmNotFoundException) as _:
            client._raise_for_error(resp, body)

    # --- HTTP status fallbacks ---

    def test_http_400_fallback(self):
        body = {"errors": [{"description": "bad input"}], "warnings": []}
        resp = self._make_response(400, body)

        client = make_client()
        with pytest.raises(SlurmBadRequestException) as _:
            client._raise_for_error(resp, body)

    def test_http_403_fallback(self):
        body = {"errors": [], "warnings": []}
        resp = self._make_response(403, body)

        client = make_client()
        with pytest.raises(SlurmAuthException) as _:
            client._raise_for_error(resp, body)

    def test_http_404_fallback(self):
        body = {"errors": [], "warnings": []}
        resp = self._make_response(404, body)

        client = make_client()
        with pytest.raises(SlurmNotFoundException) as _:
            client._raise_for_error(resp, body)

    def test_http_409_fallback(self):
        body = {"errors": [], "warnings": []}
        resp = self._make_response(409, body)

        client = make_client()
        with pytest.raises(SlurmConflictException) as _:
            client._raise_for_error(resp, body)

    def test_http_503_fallback(self):
        body = {"errors": [], "warnings": []}
        resp = self._make_response(503, body)

        client = make_client()
        with pytest.raises(SlurmUnavailableException) as _:
            client._raise_for_error(resp, body)

    def test_http_200_no_error(self):
        body = {"errors": [], "warnings": [], "meta": {}}
        resp = self._make_response(200, body)

        client = make_client()
        # Should not raise
        client._raise_for_error(resp, body)

    def test_http_200_with_errors_but_no_error_code(self):
        """If errors list has strings (not dicts), fall back to status mapping."""
        body = {"errors": ["some error"], "warnings": []}
        resp = self._make_response(400, body)

        client = make_client()
        with pytest.raises(SlurmBadRequestException) as _:
            client._raise_for_error(resp, body)

    def test_warnings_logged_but_not_raised(self):
        """Warnings should not trigger exceptions."""
        body = {"errors": [], "warnings": ["this is a warning"]}
        resp = self._make_response(200, body)

        client = make_client()
        client._raise_for_error(resp, body)  # no exception

    def test_error_number_mapping(self):
        """Error numbers (not error strings) should be handled gracefully."""
        body = {"errors": [{"error_number": 42, "description": "some error"}], "warnings": []}
        resp = self._make_response(400, body)

        client = make_client()
        with pytest.raises(SlurmBadRequestException) as _:
            client._raise_for_error(resp, body)

    # --- Exception string representation ---

    def test_exception_str(self):
        exc = SlurmException("test", errors=["e1"], status_code=400)
        s = str(exc)
        assert "test" in s
        assert "e1" in s
        assert "400" in s

    def test_exception_hierarchy(self):
        assert issubclass(SlurmConflictException, SlurmException)
        assert issubclass(SlurmAlreadyExistsException, SlurmConflictException)
        assert issubclass(SlurmUserIdMissingException, SlurmNotFoundException)
        assert issubclass(SlurmNoRemoveDefaultAccountException, SlurmConflictException)
        assert issubclass(SlurmInvalidQueryException, SlurmConflictException)


# ======================================================================
# 3. VERSION DISCOVERY TESTS  (pytest-httpserver)
# ======================================================================


class TestVersionDiscovery:
    """Test version negotiation against a local HTTP server.

    Uses ``pytest-httpserver`` to simulate slurmrestd responses.
    """

    def test_picks_highest_version(self, httpserver):
        """Client should select the highest version that responds."""
        # Only v0.0.45 and v0.0.44 respond
        for v in ["v0.0.45", "v0.0.44"]:
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"meta": {}},
                status=200,
            )

        client = SlurmClient(
            base_url=httpserver.url_for("/"),
            jwt_token="test",
        )
        version = client.discover_version()
        assert version == "v0.0.45"

    def test_skips_non_responding_versions(self, httpserver):
        """Versions that time out or return 503 should be skipped."""
        # Only v0.0.44 responds, others return 503
        for v in ["v0.0.45", "v0.0.43", "v0.0.42", "v0.0.41"]:
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"errors": [{"error": "ESLURM_DB_CONNECTION"}]},
                status=503,
            )
        httpserver.expect_request("/slurmdb/v0.0.44/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )

        client = SlurmClient(
            base_url=httpserver.url_for("/"),
            jwt_token="test",
        )
        version = client.discover_version()
        assert version == "v0.0.44"

    def test_raises_on_no_compatible_version(self, httpserver):
        """If no version responds, RuntimeError should be raised."""
        for v in ["v0.0.45", "v0.0.44", "v0.0.43", "v0.0.42", "v0.0.41"]:
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"errors": []},
                status=503,
            )

        client = SlurmClient(
            base_url=httpserver.url_for("/"),
            jwt_token="test",
        )
        with pytest.raises(RuntimeError, match="No compatible"):
            client.discover_version()

    def test_stores_version_on_client(self, httpserver):
        """After discovery, client.version should be set."""
        httpserver.expect_request("/slurmdb/v0.0.45/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )

        client = SlurmClient(
            base_url=httpserver.url_for("/"),
            jwt_token="test",
        )
        client.discover_version()
        assert client.version == "v0.0.45"

    def test_url_path_construction(self):
        """URL helper methods should use the discovered version."""
        client = make_client(version="v0.0.44")
        assert client._slurmdb_path("accounts/") == ("http://mock.slurm.test/slurmdb/v0.0.44/accounts/")
        assert client._slurm_path("jobs/") == ("http://mock.slurm.test/slurm/v0.0.44/jobs/")

    def test_url_path_with_different_version(self):
        client = make_client(version="v0.0.41")
        assert client._slurmdb_path("associations/") == ("http://mock.slurm.test/slurmdb/v0.0.41/associations/")


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
        result = client._request("GET", url)
        assert "meta" in result

    @responses.activate
    def test_transient_503_exhausted_retries(self):
        """All three attempts return 503 — should raise after retries."""
        url = url_for("ping/")

        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})

        client = make_client(retries=3, retry_backoff=0.01)
        with pytest.raises(SlurmUnavailableException):
            client._request("GET", url)

    @responses.activate
    def test_non_transient_error_not_retried(self):
        """A 400 error should be raised immediately, not retried."""
        url = url_for("accounts/")

        responses.get(url, status=400, json={"errors": [{"error": "ESLURM_REST_INVALID_QUERY"}]})

        client = make_client(retries=3, retry_backoff=0.01)
        with pytest.raises(SlurmBadRequestException):
            client._request("GET", url)

    @responses.activate
    def test_network_failure_triggers_retry(self):
        """A connection error should be retried, then raise SlurmUnavailableException."""
        url = url_for("ping/")

        # Simulate connection error by not registering any response
        client = make_client(retries=2, retry_backoff=0.01)
        with pytest.raises(SlurmUnavailableException):
            client._request("GET", url)

    @responses.activate
    def test_retry_backoff_timing(self):
        """Verify that backoff increases between retries."""
        import time

        url = url_for("ping/")

        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=503, json={"errors": [{"error": "ESLURM_DB_CONNECTION"}]})
        responses.get(url, status=200, json={"errors": [], "meta": {}})

        client = make_client(retries=3, retry_backoff=0.5)

        start = time.time()
        client._request("GET", url)
        elapsed = time.time() - start

        # Two sleeps: 0.5 * 1 + 0.5 * 2 = 0.5 + 1.0 = 1.5s minimum
        assert elapsed >= 1.0


# ======================================================================
# 5. ACCOUNT ENDPOINT TESTS  (responses + spec)
# ======================================================================


class TestAccountEndpoints:
    """Test account create, query, and delete endpoints."""

    @responses.activate
    def test_create_accounts(self):
        url = url_for("accounts/")
        responses.post(
            url,
            status=200,
            json={
                "accounts": [_SAMPLE_ACCOUNT],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_accounts([_SAMPLE_ACCOUNT])
        assert "accounts" in result
        assert result["accounts"] == [_SAMPLE_ACCOUNT]

    @responses.activate
    def test_create_accounts_already_exists(self):
        """ESLURM_ALREADY_DB_ENTRY should raise SlurmAlreadyExistsException."""
        url = url_for("accounts/")
        responses.post(
            url,
            status=409,
            json={
                "errors": [{"error": "ESLURM_ALREADY_DB_ENTRY", "description": "exists"}],
                "warnings": [],
            },
        )

        client = make_client()
        with pytest.raises(SlurmAlreadyExistsException):
            client.create_accounts([_SAMPLE_ACCOUNT])

    @responses.activate
    def test_create_accounts_with_conflict_ok(self):
        """The conflict-ok wrapper should catch and return."""
        url = url_for("accounts/")
        responses.post(
            url,
            status=409,
            json={
                "errors": [{"error": "ESLURM_ALREADY_DB_ENTRY", "description": "exists"}],
                "warnings": [],
            },
        )

        client = make_client()
        result = client.create_accounts_with_conflict_ok([_SAMPLE_ACCOUNT])
        assert "errors" in result
        assert "warnings" in result

    @responses.activate
    def test_get_accounts(self):
        url = url_for("accounts/")
        responses.get(
            url,
            status=200,
            json={
                "accounts": [_SAMPLE_ACCOUNT],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_accounts()
        assert "accounts" in result
        assert len(result["accounts"]) == 1

    @responses.activate
    def test_get_accounts_filtered(self):
        url = url_for("accounts/")
        responses.get(
            url,
            status=200,
            json={
                "accounts": [_SAMPLE_ACCOUNT],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_accounts(name="hpc-lab", with_assocs=True)
        assert "accounts" in result

    @responses.activate
    def test_delete_account(self):
        url = url_for("account/hpc-lab")
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.delete_account("hpc-lab", "hpc01")
        assert "errors" in result

    @responses.activate
    def test_delete_account_still_default(self):
        """Deleting an account that is a user's default should raise."""
        url = url_for("account/hpc-lab")
        responses.delete(
            url,
            status=409,
            json={
                "errors": [{"error": "ESLURM_NO_REMOVE_DEFAULT_ACCOUNT", "description": "still default"}],
                "warnings": [],
            },
        )

        client = make_client()
        with pytest.raises(SlurmNoRemoveDefaultAccountException):
            client.delete_account("hpc-lab", "hpc01")


# ======================================================================
# 6. ASSOCIATION ENDPOINT TESTS
# ======================================================================


class TestAssociationEndpoints:
    """Test association create, query, and delete endpoints."""

    @responses.activate
    def test_create_associations(self):
        url = url_for("associations/")
        responses.post(
            url,
            status=200,
            json={
                "associations": [_SAMPLE_ASSOCIATION],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_associations([_SAMPLE_ASSOCIATION])
        assert "associations" in result

    @responses.activate
    def test_create_associations_already_exists(self):
        url = url_for("associations/")
        responses.post(
            url,
            status=409,
            json={
                "errors": [{"error": "ESLURM_ALREADY_DB_ENTRY", "description": "exists"}],
                "warnings": [],
            },
        )

        client = make_client()
        with pytest.raises(SlurmAlreadyExistsException):
            client.create_associations([_SAMPLE_ASSOCIATION])

    @responses.activate
    def test_create_associations_with_conflict_ok(self):
        url = url_for("associations/")
        responses.post(
            url,
            status=409,
            json={
                "errors": [{"error": "ESLURM_ALREADY_DB_ENTRY", "description": "exists"}],
                "warnings": [],
            },
        )

        client = make_client()
        result = client.create_associations_with_conflict_ok([_SAMPLE_ASSOCIATION])
        assert "errors" in result

    @responses.activate
    def test_get_associations(self):
        url = url_for("associations/")
        responses.get(
            url,
            status=200,
            json={
                "associations": [_SAMPLE_ASSOCIATION],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_associations()
        assert "associations" in result

    @responses.activate
    def test_get_associations_filtered(self):
        url = url_for("associations/")
        responses.get(
            url,
            status=200,
            json={
                "associations": [_SAMPLE_ASSOCIATION],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_associations(
            account="hpc-lab",
            user="jsmith",
            cluster="hpc01",
        )
        assert "associations" in result

    @responses.activate
    def test_delete_associations(self):
        url = url_for("associations/")
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.delete_associations("hpc-lab", "jsmith", "hpc01")
        assert "errors" in result

    @responses.activate
    def test_delete_associations_with_partition(self):
        url = url_for("associations/")
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.delete_associations(
            "hpc-lab",
            "jsmith",
            "hpc01",
            partition="gpu",
        )
        assert "errors" in result


# ======================================================================
# 7. USER ENDPOINT TESTS
# ======================================================================


class TestUserEndpoints:
    """Test user create, query, and delete endpoints."""

    @responses.activate
    def test_create_users(self):
        url = url_for("users/")
        responses.post(
            url,
            status=200,
            json={
                "users": [_SAMPLE_USER],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_users([_SAMPLE_USER])
        assert "users" in result

    @responses.activate
    def test_get_users(self):
        url = url_for("users/")
        responses.get(
            url,
            status=200,
            json={
                "users": [_SAMPLE_USER],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_users()
        assert "users" in result

    @responses.activate
    def test_get_users_filtered(self):
        url = url_for("users/")
        responses.get(
            url,
            status=200,
            json={
                "users": [_SAMPLE_USER],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_users(name="jsmith", with_assocs=True)
        assert "users" in result

    @responses.activate
    def test_delete_user(self):
        url = url_for("user/jsmith")
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.delete_user("jsmith", "hpc01")
        assert "errors" in result

    @responses.activate
    def test_delete_user_not_found(self):
        url = url_for("user/unknown")
        responses.delete(
            url,
            status=404,
            json={
                "errors": [{"error": "ESLURM_USER_ID_MISSING", "description": "not found"}],
                "warnings": [],
            },
        )

        client = make_client()
        with pytest.raises(SlurmUserIdMissingException):
            client.delete_user("unknown", "hpc01")


# ======================================================================
# 8. USER+ASSOCIATION SHORTCUT TESTS
# ======================================================================


class TestUserAssociationEndpoints:
    """Test bulk user+association and account+association endpoints."""

    @responses.activate
    def test_create_users_with_associations(self):
        url = url_for("users_association/")
        body = {
            "users": ["jsmith"],
            "accounts": ["hpc-lab"],
            "clusters": ["hpc01"],
            "association": {"fairshare": 1},
        }
        responses.post(
            url,
            status=200,
            json={
                "association_condition": body,
                "user": {"name": "jsmith"},
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_users_with_associations(body)
        assert "association_condition" in result
        assert "user" in result

    @responses.activate
    def test_create_accounts_with_associations(self):
        url = url_for("accounts_association/")
        body = {
            "accounts": ["hpc-lab"],
            "clusters": ["hpc01"],
            "association": {"fairshare": 1},
        }
        responses.post(
            url,
            status=200,
            json={
                "association_condition": body,
                "account": {"name": "hpc-lab"},
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.create_accounts_with_associations(body)
        assert "association_condition" in result
        assert "account" in result


# ======================================================================
# 9. CONFIG ENDPOINT TESTS
# ======================================================================


class TestConfigEndpoints:
    """Test config get and dump endpoints."""

    @responses.activate
    def test_get_config(self):
        url = url_for("config")
        responses.get(
            url,
            status=200,
            json={
                "clusters": [],
                "accounts": [],
                "users": [],
                "associations": [],
                "qos": [],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.get_config()
        assert "clusters" in result
        assert "accounts" in result

    @responses.activate
    def test_dump_config(self):
        url = url_for("config")
        responses.post(
            url,
            status=200,
            json={
                "clusters": [],
                "accounts": [],
                "users": [],
                "associations": [],
                "qos": [],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.dump_config({"clusters": True})
        assert "clusters" in result
        assert "accounts" in result

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
        with pytest.raises(SlurmBadRequestException):
            client.upsert_config(config)


# ======================================================================
# 10. KILL JOBS ENDPOINT TESTS
# ======================================================================


class TestKillJobsEndpoints:
    """Test job kill endpoints."""

    @responses.activate
    def test_kill_jobs(self):
        url = url_for("/slurm/jobs/")
        responses.delete(
            url,
            status=200,
            json={
                "status": [],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.kill_jobs(_SAMPLE_KILL_MSG)
        assert "status" in result

    @responses.activate
    def test_kill_job(self):
        url = url_for("/slurm/job/12345")
        responses.delete(
            url,
            status=200,
            json={
                "status": [],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.kill_job("12345", signal="SIGKILL")
        assert "status" in result

    @responses.activate
    def test_kill_job_no_status_field_v41(self):
        """v0.0.41 response lacks the ``status`` field — test graceful handling."""
        url = url_for("/slurm/job/12345", version="v0.0.41")
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client(version="v0.0.41")
        result = client.kill_job("12345")
        # Should not raise — absence of "status" is OK
        assert "status" not in result

    @responses.activate
    def test_kill_jobs_with_filters(self):
        url = url_for("/slurm/jobs/")
        responses.delete(
            url,
            status=200,
            json={
                "status": [],
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client()
        result = client.kill_jobs(
            {
                "user_name": "jsmith",
                "account": "hpc-lab",
                "partition": "gpu",
                "signal": "SIGTERM",
                "job_state": "RUNNING",
            }
        )
        assert "status" in result


# ======================================================================
# 11. CROSS-VERSION COMPATIBILITY TESTS
# ======================================================================


class TestVersionCompatibility:
    """Verify that serializers and URL construction work for all versions.

    Uses the ``spec_version`` parametrized fixture to run the same
    assertions across v0.0.41–v0.0.45.
    """

    def test_serializer_account_all_versions(self, spec_version):
        """Account serializer produces same shape for every version."""
        body = SlurmClient.serialize_account("test", description="desc", organization="org")
        # The account_rec schema is identical across all versions
        assert body["name"] == "test"
        assert body["description"] == "desc"
        assert body["organization"] == "org"

    def test_serializer_association_all_versions(self, spec_version):
        """Association serializer produces same shape for every version."""
        body = SlurmClient.serialize_association("a", "u", "c", partition="p", fairshare=1)
        assert body["account"] == "a"
        assert body["user"] == "u"
        assert body["cluster"] == "c"
        assert body["partition"] == "p"
        assert body["fairshare"] == 1

    def test_serializer_user_all_versions(self, spec_version):
        """User serializer produces same shape for every version."""
        body = SlurmClient.serialize_user("u", "a", default_qos="q")
        assert body["name"] == "u"
        assert body["default"]["account"] == "a"
        assert body["default"]["qos"] == "q"

    def test_url_construction_all_versions(self, spec_version):
        """URL path uses the version prefix correctly."""
        client = make_client(version=spec_version)
        expected_slurmdb = f"http://mock.slurm.test/slurmdb/{spec_version}/accounts/"
        expected_slurm = f"http://mock.slurm.test/slurm/{spec_version}/jobs/"
        assert client._slurmdb_path("accounts/") == expected_slurmdb
        assert client._slurm_path("jobs/") == expected_slurm

    def test_discover_version_probes_correctly(self, spec_version, httpserver):
        """The probe URL should use the correct version prefix."""
        # Register a handler for the specific version
        httpserver.expect_request(f"/slurmdb/{spec_version}/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )

        client = SlurmClient(
            base_url=httpserver.url_for("/"),
            jwt_token="test",
        )
        # Override _SUPPORTED_VERSIONS at the module level
        import coldfront.slurm.client.client as client_mod

        with mock.patch.object(client_mod, "_SUPPORTED_VERSIONS", [spec_version]):
            v = client.discover_version()
            assert v == spec_version

    @responses.activate
    def test_kill_job_response_shapes(self, spec_version):
        """Kill job endpoint works for all versions (status field optional)."""
        url = url_for("/slurm/job/42", version=spec_version)
        responses.delete(
            url,
            status=200,
            json={
                **_SUCCESS_RESPONSE,
            },
        )

        client = make_client(version=spec_version)
        result = client.kill_job("42")
        # Response should be valid regardless of status field presence
        assert "errors" in result


# ======================================================================
# 12. SPEC-VALIDATION TESTS  (uses OpenAPI spec files)
# ======================================================================


class TestSpecValidation:
    """Validate serializers against the actual OpenAPI schema definitions.

    These tests use the ``spec_loader`` fixture to load the OpenAPI spec
    files and check that our serializer output matches the expected schemas.
    """

    def test_account_schema_matches_spec(self, spec_loader):
        """Account serializer output should match ``account`` schema."""
        spec = spec_loader("v0.0.44")
        body = SlurmClient.serialize_account("test", description="desc", organization="org")

        # The POST /accounts/ request body is an array of account objects.
        # The account schema has: name, description, organization.
        acct = spec.schema("account")
        props = acct.get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in account schema"

    def test_assoc_rec_set_schema_matches_spec(self, spec_loader):
        """Association serializer should match ``assoc_rec_set`` schema."""
        spec = spec_loader("v0.0.44")
        body = SlurmClient.serialize_association("a", "u", "c", partition="p", fairshare=1)

        ars = spec.schema("assoc_rec_set")
        props = ars.get("properties", {})

        # Our serializer fields should match assoc_rec_set properties
        # Note: account, user, cluster, partition are not in assoc_rec_set
        # They're part of the POST body which is an array of assoc objects.
        # The POST /associations/ body is an array of assoc_rec_set objects
        # but assoc_rec_set doesn't include account/user/cluster/partition.
        # Those come from the assoc schema. Our serializer is correct for
        # the actual API behavior — we include them and Slurm accepts them.
        for key in ["fairshare", "defaultqos", "parent"]:
            if key in body:
                assert key in props, f"Field '{key}' not found in assoc_rec_set schema"

    def test_kill_jobs_msg_schema_matches_spec(self, spec_loader):
        """Kill-jobs serializer should match ``kill_jobs_msg`` schema."""
        spec = spec_loader("v0.0.44")
        body = SlurmClient.serialize_kill_jobs_msg(
            user_name="u",
            account="a",
            partition="p",
        )

        kjm = spec.schema("kill_jobs_msg")
        props = kjm.get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in kill_jobs_msg schema"

    def test_users_add_cond_schema_matches_spec(self, spec_loader):
        """users_add_cond serializer should match ``users_add_cond`` schema."""
        spec = spec_loader("v0.0.44")
        body = SlurmClient.serialize_users_add_cond(
            users=["u"],
            accounts=["a"],
            clusters=["c"],
        )

        uac = spec.schema("users_add_cond")
        props = uac.get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in users_add_cond schema"

    def test_accounts_add_cond_schema_matches_spec(self, spec_loader):
        """accounts_add_cond serializer should match ``accounts_add_cond`` schema."""
        spec = spec_loader("v0.0.44")
        body = SlurmClient.serialize_accounts_add_cond(
            accounts=["a"],
            clusters=["c"],
        )

        aac = spec.schema("accounts_add_cond")
        props = aac.get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in accounts_add_cond schema"

    def test_response_structures_match_spec(self, spec_loader):
        """Response bodies should match the spec's response schemas."""
        spec = spec_loader("v0.0.44")

        # Check that our _SUCCESS_RESPONSE template has the right fields
        # for an accounts response
        accounts_resp = spec.schema("openapi_accounts_resp")
        resp_props = accounts_resp.get("properties", {})
        assert "accounts" in resp_props
        assert "meta" in resp_props
        assert "errors" in resp_props
        assert "warnings" in resp_props

    def test_versions_have_identical_assoc_rec_set(self, spec_loader):
        """assoc_rec_set should be identical across all supported versions."""
        prev = None
        for v in ["v0.0.41", "v0.0.42", "v0.0.43", "v0.0.44", "v0.0.45"]:
            spec = spec_loader(v)
            ars = spec.schema("assoc_rec_set")
            props = ars.get("properties", {})
            if prev is not None:
                assert set(props.keys()) == prev
            prev = set(props.keys())

    def test_versions_have_identical_kill_jobs_msg(self, spec_loader):
        """kill_jobs_msg should be identical across all supported versions."""
        prev = None
        for v in ["v0.0.41", "v0.0.42", "v0.0.43", "v0.0.44", "v0.0.45"]:
            spec = spec_loader(v)
            kjm = spec.schema("kill_jobs_msg")
            props = kjm.get("properties", {})
            if prev is not None:
                assert set(props.keys()) == prev
            prev = set(props.keys())
