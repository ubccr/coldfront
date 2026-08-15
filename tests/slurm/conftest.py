# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Pytest fixtures for Slurm REST API client tests.

Provides:
- ``spec_loader`` — loads OpenAPI spec files and extracts schemas
- ``spec_version`` — parametrized fixture iterating over v0.0.41–v0.0.45
- ``mock_response`` — builds realistic response bodies from spec schemas
- ``mock_client`` — constructs a :class:`SlurmClient` with a fake version
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from coldfront.slurm.client import SlurmClient

# ---------------------------------------------------------------------------
# Path to the checked-in OpenAPI spec files
# ---------------------------------------------------------------------------
_SPEC_DIR = Path(__file__).resolve().parent / "specs"
_SUPPORTED_VERSIONS = ["v0.0.41", "v0.0.42", "v0.0.43", "v0.0.44", "v0.0.45"]


# ---------------------------------------------------------------------------
# Spec loader fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def spec_loader():
    """Fixture providing a helper to load and query OpenAPI spec files.

    Usage in tests::

        def test_something(spec_loader):
            spec = spec_loader("v0.0.44")
            # Access components
            assoc_set = spec.schema("assoc_rec_set")
            # Access paths
            assoc_path = spec.path("/slurmdb/v0.0.44/associations/")
    """

    class SpecHelper:
        def __init__(self, version: str):
            self.version = version
            # Convert v0.0.44 -> v44 to match spec filename pattern
            short_ver = version.replace("0.0.", "")  # "v0.0.44" -> "v44"
            path = _SPEC_DIR / f"openapi_spec_{short_ver}.json"
            with open(path) as f:
                self._raw = json.load(f)
            self.components = self._raw.get("components", {}).get("schemas", {})
            self.paths = self._raw.get("paths", {})

        def schema(self, name: str) -> dict[str, Any]:
            """Look up a component schema by name (version prefix auto-added)."""
            key = f"{self.version}_{name}"
            if key in self.components:
                return self.components[key]
            # Fallback: try raw name
            return self.components.get(name, {})

        def path(self, url: str) -> dict[str, Any]:
            """Look up a path definition."""
            return self.paths.get(url, {})

        def response_body(
            self,
            url: str,
            method: str = "GET",
            status: int = 200,
            extra: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            """Build a realistic response body from a path's 200 response schema.

            Walks the ``$ref`` chain and fills in minimal placeholder values.
            Returns a dict with ``meta``, ``errors``, ``warnings``, and the
            entity field (e.g., ``accounts``, ``associations``, ``users``).
            """
            path_def = self.path(url)
            if not path_def:
                return {"errors": [], "warnings": [], "meta": {}}

            op = path_def.get(method, {})
            resp_schema_ref = (
                op.get("responses", {})
                .get(str(status), {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("$ref", "")
            )

            body: dict[str, Any] = {
                "meta": {"plugin": {}, "client": {}, "slurm": {}},
                "errors": [],
                "warnings": [],
            }

            if resp_schema_ref:
                schema_name = resp_schema_ref.split("/")[-1]
                resp_schema = self.components.get(schema_name, {})
                for field_name, field_def in resp_schema.get("properties", {}).items():
                    ref = field_def.get("$ref", "")
                    if ref:
                        list_schema = self.components.get(ref.split("/")[-1], {})
                        if list_schema.get("type") == "array":
                            body[field_name] = []
                    else:
                        body[field_name] = None

            if extra:
                body.update(extra)

            return body

        def request_body_schema(self, url: str, method: str = "POST") -> dict[str, Any]:
            """Extract the request body schema for a given path+method.

            Returns the resolved schema dict (not a $ref string).
            """
            path_def = self.path(url)
            if not path_def:
                return {}

            op = path_def.get(method, {})
            req_body = op.get("requestBody", {})
            content = req_body.get("content", {})
            schema = content.get("application/json", {}).get("schema", {})
            if not schema:
                schema = content.get("application/yaml", {}).get("schema", {})

            ref = schema.get("$ref", "")
            if ref:
                schema_name = ref.split("/")[-1]
                return self.components.get(schema_name, {})
            return schema

    def factory(version: str = "v0.0.44"):
        return SpecHelper(version)

    return factory


# ---------------------------------------------------------------------------
# Parametrized version fixture
# ---------------------------------------------------------------------------


@pytest.fixture(params=_SUPPORTED_VERSIONS)
def spec_version(request):
    """Parametrized fixture yielding each supported API version.

    Use this to run the same test across all five API versions::

        def test_serializer_across_versions(spec_version):
            spec = spec_loader(spec_version)
            ...
    """
    return request.param


# ---------------------------------------------------------------------------
# Mock client factory
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Fixture that constructs a ``SlurmClient`` with a fixed version.

    The client's ``_request`` method is **not** mocked — HTTP mocking
    is done at the ``requests`` level with ``responses`` in each test.
    """

    def factory(
        base_url: str = "http://mock.slurm.test",
        jwt_token: str = "test-token",
        version: str = "v0.0.44",
        **kwargs,
    ) -> SlurmClient:
        return SlurmClient(
            base_url=base_url,
            jwt_token=jwt_token,
            version=version,
            **kwargs,
        )

    return factory


# ---------------------------------------------------------------------------
# Helper: build minimal placeholder for any schema
# ---------------------------------------------------------------------------


def _placeholder_for_schema(schema: dict[str, Any]) -> Any:
    """Generate a minimal placeholder value matching a JSON Schema.

    Used to construct realistic mock response bodies from spec schemas.
    """
    schema_type = schema.get("type", "object")
    if schema_type == "object":
        result: dict[str, Any] = {}
        for prop_name, prop_def in schema.get("properties", {}).items():
            result[prop_name] = _placeholder_for_schema(prop_def)
        return result
    elif schema_type == "array":
        items_schema = schema.get("items", {})
        return [_placeholder_for_schema(items_schema)]
    elif schema_type == "string":
        return ""
    elif schema_type == "integer":
        return 0
    elif schema_type == "boolean":
        return False
    elif schema_type == "number":
        return 0.0
    else:
        return None
