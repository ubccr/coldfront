# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm version layer: version mapping, REST API discovery,
cross-version compatibility, and OpenAPI spec conformance.

Organized by test class:

- ``TestVersionsMapping`` — versions.py helpers (single source of truth)
- ``TestVersionDiscovery`` — /ping probes against a local HTTP server
- ``TestVersionCompatibility`` — URL construction / discovery per version
- ``TestSpecValidation`` — serializer wire-format vs OpenAPI specs
"""

from unittest import mock

import pytest
import responses

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.versions import (
    api_version_for,
    is_supported,
    slurm_version_for,
    supported_api_versions,
    supported_slurm_versions,
)

_DEFAULT_BASE = "http://mock.slurm.test"
_DEFAULT_JWT = "test-token"
_DEFAULT_VER = supported_slurm_versions()[0]

_SUCCESS_RESPONSE = {
    "meta": {"plugin": {}, "client": {}, "slurm": {}},
    "errors": [],
    "warnings": [],
}


def make_client(
    base_url: str = _DEFAULT_BASE,
    jwt_token: str = _DEFAULT_JWT,
    version: str = _DEFAULT_VER,
    **kwargs,
) -> SlurmClient:
    return SlurmClient(
        base_url=base_url,
        jwt_token=jwt_token,
        version=version,
        **kwargs,
    )


def url_for(path_template: str, version: str = _DEFAULT_VER) -> str:
    api = api_version_for(version)
    if path_template.startswith("/slurm/"):
        return f"{_DEFAULT_BASE}/slurm/{api}/{path_template[len('/slurm/') :]}"
    return f"{_DEFAULT_BASE}/slurmdb/{api}/{path_template.lstrip('/')}"


# ======================================================================
# 1. VERSION MAPPING  (pure Python, no HTTP)
# ======================================================================


class TestVersionsMapping:
    """versions.py is the single source of truth for version pairs."""

    def test_supported_versions_are_slurm_releases(self):
        """supported_slurm_versions returns Slurm releases, not API versions."""
        assert supported_slurm_versions()
        for v in supported_slurm_versions():
            assert is_supported(v)

    def test_supported_api_versions_are_descending_preference(self):
        """supported_api_versions returns REST API versions in probe order."""
        assert supported_api_versions()
        assert len(supported_api_versions()) == len(supported_slurm_versions())

    def test_api_version_for_round_trips(self):
        """api_version_for maps a Slurm release to its REST API version."""
        for slurm in supported_slurm_versions():
            assert api_version_for(slurm) in supported_api_versions()

    def test_slurm_version_for_inverts_api_version(self):
        """slurm_version_for maps an API version back to its Slurm release."""
        for api in supported_api_versions():
            assert slurm_version_for(api) in supported_slurm_versions()
            # round-trip: slurm -> api -> slurm
            assert slurm_version_for(api_version_for(slurm_version_for(api))) == slurm_version_for(api)

    def test_is_supported_rejects_unknown(self):
        """An unsupported release is rejected."""
        assert not is_supported("99.99.0")


# ======================================================================
# 2. VERSION DISCOVERY  (pytest-httpserver)
# ======================================================================


class TestVersionDiscovery:
    """Test version negotiation against a local HTTP server."""

    def test_picks_highest_version(self, httpserver):
        """Client should select the highest version that responds."""
        for v in supported_api_versions():
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"meta": {}},
                status=200,
            )

        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        assert client.discover_version() == supported_api_versions()[0]

    def test_falls_back_to_next_version(self, httpserver):
        """A 503 or 404 probe is skipped in favor of the next version."""
        # Highest preferred version is unresponsive (503) — falls to next
        httpserver.expect_request(f"/slurmdb/{supported_api_versions()[0]}/ping/").respond_with_json(
            {"errors": [{"error": "ESLURM_DB_CONNECTION"}]},
            status=503,
        )
        httpserver.expect_request(f"/slurmdb/{supported_api_versions()[1]}/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )
        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        assert client.discover_version() == supported_api_versions()[1]

        # Unknown version path returns 404 — also skipped, next version wins
        httpserver.expect_request(f"/slurmdb/{supported_api_versions()[0]}/ping/").respond_with_json(
            {"errors": []},
            status=404,
        )
        httpserver.expect_request(f"/slurmdb/{supported_api_versions()[1]}/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )
        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        assert client.discover_version() == supported_api_versions()[1]

    def test_raises_on_no_compatible_version(self, httpserver):
        """If no version responds, RuntimeError should be raised."""
        for v in supported_api_versions():
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"errors": []},
                status=503,
            )

        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        with pytest.raises(RuntimeError, match="No compatible"):
            client.discover_version()

    def test_refuses_unsupported_version(self, httpserver):
        """A slurmrestd exposing only an unsupported version is refused.

        Older API versions (v0.0.41-43 -> Slurm 24.05/24.11/25.05) are NOT
        supported; discovery is strict and must raise rather than silently
        use an untested schema.
        """
        httpserver.expect_request("/slurmdb/v0.0.43/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )
        for v in supported_api_versions():
            httpserver.expect_request(f"/slurmdb/{v}/ping/").respond_with_json(
                {"errors": []},
                status=404,
            )

        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        with pytest.raises(RuntimeError, match="No compatible"):
            client.discover_version()
        assert client.version is None

    def test_stores_version_on_client(self, httpserver):
        """After discovery, client.version is the Slurm release, _api_version the API version."""
        api = supported_api_versions()[0]
        httpserver.expect_request(f"/slurmdb/{api}/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )

        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        client.discover_version()
        assert client.version == slurm_version_for(api)
        assert client._api_version == api


# ======================================================================
# 3. CROSS-VERSION COMPATIBILITY
# ======================================================================


class TestVersionCompatibility:
    """URL construction and discovery work for every supported version.

    Serializers are version-agnostic (covered once in test_client.py), so
    only the genuinely version-dependent behavior is re-run per version.
    """

    def test_url_construction_all_versions(self, spec_version):
        """URL path uses the resolved API version prefix correctly."""
        client = make_client(version=slurm_version_for(spec_version))
        assert client._slurmdb_path("accounts/") == (f"http://mock.slurm.test/slurmdb/{spec_version}/accounts/")
        assert client._slurm_path("jobs/") == (f"http://mock.slurm.test/slurm/{spec_version}/jobs/")

    def test_discover_version_probes_correctly(self, spec_version, httpserver):
        """The probe URL should use the correct version prefix."""
        httpserver.expect_request(f"/slurmdb/{spec_version}/ping/").respond_with_json(
            {"meta": {}},
            status=200,
        )

        client = SlurmClient(base_url=httpserver.url_for("/"), jwt_token="test")
        import coldfront.slurm.client.client as client_mod

        with mock.patch.object(client_mod, "SUPPORTED_API_VERSIONS", [spec_version]):
            assert client.discover_version() == spec_version

    @responses.activate
    def test_kill_job_response_shapes(self, spec_version):
        """Kill job endpoint works for all versions (status field optional)."""
        url = url_for("/slurm/job/42", version=slurm_version_for(spec_version))
        responses.delete(url, status=200, json={**_SUCCESS_RESPONSE})

        client = make_client(version=slurm_version_for(spec_version))
        result = client.kill_job("42")
        assert "errors" in result


# ======================================================================
# 4. SPEC VALIDATION  (OpenAPI spec files)
# ======================================================================


class TestSpecValidation:
    """Validate serializers against the actual OpenAPI schema definitions."""

    def test_account_schema_matches_spec(self, spec_loader):
        spec = spec_loader(supported_api_versions()[1])
        body = SlurmClient.serialize_account("test", description="desc", organization="org")

        acct = spec.schema("account")
        props = acct.get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in account schema"

    def test_assoc_schema_matches_spec(self, spec_loader):
        """The plain POST /associations/ endpoint parses the nested ``assoc``
        schema (not the flat assoc_rec_set). Validate every emitted key/path."""
        spec = spec_loader(supported_api_versions()[1])
        body = SlurmClient.serialize_association(
            "a",
            "u",
            "c",
            partition="p",
            fairshare=1,
            default_qos="normal",
            parent="root",
            max_jobs=10,
            grp_tres={"cpu": 5},
            qoslevel=["normal"],
        )

        props = spec.schema("assoc").get("properties", {})

        def walk(node, keys):
            for key in keys[:-1]:
                node = node[key].get("properties", {})
            assert keys[-1] in node

        for key in ["account", "user", "cluster", "partition", "shares_raw", "parent_account", "qos"]:
            if key in body:
                assert key in props, f"Field '{key}' not found in assoc schema"
        walk(props, ["default", "qos"])
        walk(props, ["max", "jobs", "active"])
        walk(props, ["max", "tres", "total"])

    def test_kill_jobs_msg_schema_matches_spec(self, spec_loader):
        spec = spec_loader(supported_api_versions()[1])
        body = SlurmClient.serialize_kill_jobs_msg(user_name="u", account="a", partition="p")

        props = spec.schema("kill_jobs_msg").get("properties", {})
        for key in body:
            assert key in props, f"Field '{key}' not found in kill_jobs_msg schema"

    def test_users_add_cond_schema_matches_spec(self, spec_loader):
        spec = spec_loader(supported_api_versions()[1])
        body = SlurmClient.serialize_users_add_cond(users=["u"], accounts=["a"], clusters=["c"])

        assert "association_condition" in body
        assert "user" in body
        cond = body["association_condition"]

        props = spec.schema("users_add_cond").get("properties", {})
        for key in cond:
            assert key in props, f"Field '{key}' not found in users_add_cond schema"

        resp = spec.schema("openapi_users_add_cond_resp")
        resp_props = resp.get("properties", {})
        assert "association_condition" in resp_props
        assert "user" in resp_props

    def test_accounts_add_cond_schema_matches_spec(self, spec_loader):
        spec = spec_loader(supported_api_versions()[1])
        body = SlurmClient.serialize_accounts_add_cond(accounts=["a"], clusters=["c"])

        assert "association_condition" in body
        cond = body["association_condition"]

        props = spec.schema("accounts_add_cond").get("properties", {})
        for key in cond:
            assert key in props, f"Field '{key}' not found in accounts_add_cond schema"

        resp = spec.schema("openapi_accounts_add_cond_resp")
        resp_props = resp.get("properties", {})
        assert "association_condition" in resp_props
        assert "account" in resp_props

    def test_response_structures_match_spec(self, spec_loader):
        spec = spec_loader(supported_api_versions()[1])

        accounts_resp = spec.schema("openapi_accounts_resp")
        resp_props = accounts_resp.get("properties", {})
        assert "accounts" in resp_props
        assert "meta" in resp_props
        assert "errors" in resp_props
        assert "warnings" in resp_props
