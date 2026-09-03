# ColdFront Slurm Integration — Test Suite

This directory contains the unit and integration tests for the ColdFront Slurm
integration, covering the REST API client, the dump file generator, the Django
ORM models, and the REST API views.

### Key Design Choices

1. **`responses` for most HTTP tests** — intercepts at `requests.Session` level, no server needed, fast (~2.4s for 113 tests). Used for all CRUD endpoint tests.

2. **`pytest-httpserver` for version discovery only** — version probing needs real TCP handshake because `responses` cannot intercept the dynamic URL probing logic that tries multiple version prefixes.

3. **OpenAPI spec files as test oracle** — the 5 spec files (`openapi_spec_v41.json` through `openapi_spec_v45.json`) are copied from the Slurm source tree. Spec-validation tests extract JSON schemas from the spec and verify that `SlurmClient` serializer output conforms. This catches mismatches when upgrading the client.

4. **Cross-version parametrization** — `spec_version` fixture iterates over `["v0.0.41", "v0.0.42", "v0.0.43", "v0.0.44", "v0.0.45"]`. Version-compatibility tests confirm that entity schemas (`assoc_rec_set`, `kill_jobs_msg`, etc.) are identical across all versions, justifying the version-agnostic client design.

5. **`spec_loader` fixture** — lazy-loads spec JSON on demand. The `SpecHelper` class provides `.schema(name)` with automatic version-prefix resolution (e.g., `"assoc_rec_set"` → `"v0.0.44_assoc_rec_set"`), hiding the version-prefixed key convention used in the OpenAPI spec files.

## Spec Files

The OpenAPI spec files live in `tests/slurm/specs/`:

```
tests/slurm/specs/
├── openapi_spec_v41.json  (401 KB)
├── openapi_spec_v42.json  (394 KB)
├── openapi_spec_v43.json  (432 KB)
├── openapi_spec_v44.json  (454 KB)
└── openapi_spec_v45.json  (520 KB)
```

These are exact copies from the Slurm source tree at:
`slurm/testsuite/python/data/openapi_spec_v{4,5}.json`

### Adding a New Spec Version

When Slurm releases a new API version (e.g., `v0.0.46`):

1. **Obtain the new spec file** — copy from the Slurm source tree:
   ```
   cp /path/to/slurm/testsuite/python/data/openapi_spec_v46.json \
      tests/slurm/specs/openapi_spec_v46.json
   ```

2. **Register the version** — add `"v0.0.46"` to `_SUPPORTED_VERSIONS` in
   `src/coldfront/slurm/client/client.py`:
   ```python
   _SUPPORTED_VERSIONS = [
       "v0.0.41",
       "v0.0.42",
       "v0.0.43",
       "v0.0.44",
       "v0.0.45",
       "v0.0.46",  # <-- add here
   ]
   ```

3. **Run the spec-validation tests** — these will automatically pick up the
   new version via the `spec_version` fixture (which iterates over all
   `.json` files in `specs/`):
   ```
   COLDFRONT_ENV=.env.testing uv run -m pytest tests/slurm/test_client.py \
       -k "TestSpecValidation" -v
   ```

4. **Check for schema differences** — if the new version changes any entity
   schema (e.g., adds required fields to `assoc_rec_set`), the
   `test_versions_have_identical_*` tests will fail. Examine the diff:
   ```
   python3 -c "
   import json
   v45 = json.load(open('tests/slurm/specs/openapi_spec_v45.json'))
   v46 = json.load(open('tests/slurm/specs/openapi_spec_v46.json'))
   # Compare the schemas that matter to us
   for name in ['assoc_rec_set', 'kill_jobs_msg', 'users_add_cond', 'accounts_add_cond',
                'account', 'user', 'account_short', 'user_short']:
       s45 = v45['components']['schemas'].get(f'v0.0.45_{name}', {})
       s46 = v46['components']['schemas'].get(f'v0.0.46_{name}', {})
       if s45 != s46:
           print(f'  {name}: CHANGED')
   "
   ```

5. **Update serializers if needed** — if schemas changed, modify the
   corresponding `serialize_*` methods in `src/coldfront/slurm/client/client.py`.
   If the changes are *additive* (new optional fields), include them
   unconditionally — older versions ignore unknown fields. If changes are
   *breaking* (renamed or removed fields), add version-conditional logic.

6. **Run the full suite** — confirm nothing regressed:
   ```
   COLDFRONT_ENV=.env.testing uv run -m pytest tests/slurm/ -v
   ```

### Automated Compatibility Check

The `TestSpecValidation::test_versions_have_identical_assoc_rec_set` and
`test_versions_have_identical_kill_jobs_msg` tests compare the entity schemas
across all loaded spec versions. If any version differs, the test fails with
a detailed diff. This is the first signal that the client may need updating.

## Running the Tests

```bash
# Full slurm test suite
COLDFRONT_ENV=.env.testing uv run -m pytest tests/slurm/

# Just the client tests
COLDFRONT_ENV=.env.testing uv run -m pytest tests/slurm/test_client.py

# With coverage
COLDFRONT_ENV=.env.testing uv run -m coverage run -m pytest tests/slurm/
COLDFRONT_ENV=.env.testing uv run -m coverage report
```
