# Slurm e2e tests

End-to-end tests against a **live Slurm cluster** — slurmdbd, slurmctld,
slurmrestd, plus MySQL and one compute worker — running ColdFront's
`SlurmClient` and sync engine against the real REST API.

## Running

```bash
COLDFRONT_E2E=1 COLDFRONT_ENV=.env.testing uv run -m pytest tests/e2e/slurm/ -m e2e
```

This brings up a real slurmdbd/slurmctld/slurmrestd (+ mysql + one compute
worker), obtains an admin JWT via `scontrol token`, and runs ColdFront's
`SlurmClient` against it. The stack is torn down (`down --volumes`) at session
end, so each run starts from a fresh database.

## What the suite covers

- **CRUD round-trips** — accounts, associations, QOS, partitions via the REST
  client, with verification read-backs.
- **Error-path contract** — how the supported versions surface auth, not-found,
  and already-present failures (auth → 502/503 unavailability, missing entities
  → silent success), locked into the client's `_ERROR_MAP`.
- **Sync** — association/QOS sync into the Django DB, idempotent re-runs.
- **Usage / billing** — `run_usage_sync` against real completed jobs.
- **Access control** — partition `AllowQOS` pushed via REST, enforced at submit.

## Layout

- `conftest.py` — the Slurm-specific fixtures: `SLURM_VERSIONS`, the
  `require_version()` gate, one `SlurmStack` per version, JWTs, clients, and
  the generic cleanup (`reset_slurm_stack` + autouse `slurm_cleanup`).
- `compose/docker-compose.slurm.yml` — trimmed, parameterized port of
  `slurm-docker-cluster` (no build blocks; pre-built images).
- `config/slurm.conf` — base config (single per version). Tests that
  need non-stock config (e.g. `TRESBillingWeights`, `AllowQOS`) push it at
  runtime via the REST API (`POST /partitions/`) instead of shipping conf
  variants.
- `test_*.py` — the live suites (client, errors, sync, usage, access).

## Supported Slurm versions

`SUPPORTED_SLURM_VERSIONS` in `src/coldfront/slurm/client/versions.py` maps
Slurm releases to the REST API version they expose (26.05.x → v0.0.45,
25.11.x → v0.0.44) and is the **single source of truth** for supported
versions. Add a release -> API entry there; the `SlurmStack` matrix
(`SLURM_VERSIONS` in `slurm/conftest.py`) derives from it automatically. Each
version gets its own isolated compose project (`COMPOSE_PROJECT_NAME`).

## JWT expiry

The e2e stack issues 7-day admin tokens:

- `slurm.conf` sets `AuthAltParameters=max_token_lifespan=604800`.
- `SlurmStack.jwt()` runs `scontrol token lifespan=604800` (root is a SlurmUser
  and exempt from the cap, but we request it explicitly).

## Adding a stack with a custom slurm.conf

`SlurmStack(version=..., slurm_conf=..., variant=...)` selects a config file
from `config/`; the file is bind-mounted **read-only** over
`/etc/slurm/slurm.conf` in both slurmctld and slurmrestd, so the conf is the
source of truth and runtime REST changes stay in-memory. The stock stack uses
`slurm_conf="slurm.conf"`. To add an entirely new conf variant:

1. **Drop a new file** in `config/` (e.g. `my-special.conf`). It is a *full*
   replacement, not a partial override.
2. **Instantiate the stack** with `slurm_conf="my-special.conf"` and a
   distinct `variant` (e.g. `"special"`), plus its `_jwt`/`_client`/`_settings`
   companions if the tests need them.

`project_name` derives from `version + conf_stem + variant`, so concurrent
stacks sharing the base conf stay isolated. One gotcha:

- **Keep the pieces the stack needs**: `ClusterName=`, the JWT auth block
  (`AuthAltTypes`/`AuthAltParameters`), `AccountingStorageEnforce`, and the
  partition/node-set names that match the `slurmd-cpu` worker's registered
  `Feature=cpu`. Renaming partitions away from `cpu` breaks node membership
  unless the worker command/feature changes too.

## Design philosophy: one reality, two lenses

ColdFront supports a **clearly stated set of Slurm versions** (see
`SUPPORTED_SLURM_VERSIONS`). There is no hypothetical "some future slurmrestd"
behavior: the tests target exactly the supported versions and nothing else.
See `tests/e2e/README.md` for the general philosophy and mock/e2e coverage
split; the Slurm-specific realities below are what live probing locked in.

## Idempotency contract

Re-creating an entity (account / association) on the live stack is **silent
success**, and the verification read-back counts an already-present entity as
success. Re-running an add_cond shortcut returns an empty body that the
read-back disambiguates to "already present". So a whole sync re-run never
raises and fills only the gaps — `TestIdempotentUpsertLive` locks this in.

## Association wire format: two parsers

Live probing showed the REST API uses **two different association parsers**:

- `POST /accounts_association/` (the add_cond shortcut that creates the
  account-level parent) parses the **flat `assoc_rec_set`** schema —
  `grptresmins`, `fairshare`, `qoslevel`, `parent`, `defaultqos`.
- `POST /associations/` (the plain, user-level endpoint) parses the **nested
  `assoc`** schema — `shares_raw`, `qos`, `parent_account`, `default/qos` and
  the nested `max/` limit paths (`max/jobs/active`, `max/tres/per/job`, ...).
  Flat `fairshare`/`qoslevel`/`parent` sent here are **silently ignored**
  ("Ignoring unknown field" warning) — the limits never materialize.

`serialize_association` therefore emits the nested `assoc` shape, while the
add_cond path keeps the flat `assoc_rec_set`. `test_sync.py` drives the real
sync engine (Django DB seeding + `slurm_settings`) and verifies the
hierarchy + limits round-trip against live `sacctmgr`.

## Usage / billing reality

`test_usage.py` drives `run_usage_sync` against the live stack using **real
completed jobs** submitted as the baked-in `cgray` user, and locks in the
billing reality probed live:

- `tres.allocated` carries a `billing` TRES. The base `slurm.conf` has no
  `TRESBillingWeights`, so billing falls back to the default `CPU=1` weight
  (billing count `1` for a 1-cpu job).
- A test sets `TRESBillingWeights=CPU=2.0,Node=3.0` at runtime on the shared
  stock stack via the REST API (`POST /partitions/` -> `tres/billing_weights`);
  a 1-cpu job then bills `5` (= 1 x 2.0 + 1 x 3.0). `TRESBillingWeights` is a
  **partition-level** option (see `doc/man/man5/slurm.conf.5`), identical in
  `sacct` AllocTRES and `get_job_usage`. This path needs `POST /partitions/`
  (v0.0.45 only), so the billing test gates on `require_version(stack,
  ">=26.05.4")` and skips on the others. The generic cleanup's reconfigure
  wipes the runtime weights after the test, so the default `CPU=1` billing of
  the other tests is never affected — no separate billing stack is needed.
- `_roll_up_job_usage`'s math (`billing_count x overlap / 3600`) matches the
  live record, so the `SlurmAccountUsage` DB row is verified against the
  **computed** value (there is no `sacct Billing` column on the live stack).
- Re-running the sync is idempotent (`update_or_create` per account/day).

Job submission needs a valid association (the stack sets
`AccountingStorageEnforce=associations`): the add_cond endpoint creates the
account + account-level parent, the plain endpoint adds the baked-in user's
assoc, then `runuser -u cgray -- sbatch --output=/dev/null` runs the job
(output must be writable — `/data` is root-owned).

One stack runs per version (stock). The billing test shares it and pushes
`TRESBillingWeights` at runtime, so no second stack is needed.

## Access-control reality

`test_access.py` verifies partition `AllowQOS` pushed at runtime via the REST
API (`POST /partitions/` -> `qos/allowed`) is enforced at job submission: a
job whose QOS is not in a partition's `AllowQOS` list is rejected at submit
(the "Invalid account or account/partition combination" message — Slurm's
no-QOS-access error). It creates its own runtime `q2` partition (sharing node
`c1`) and pushes `AllowQOS=cpu` on `cpu`, then checks the 4-way `--qos` matrix
and the association `default_qos` scenarios. The autouse `slurm_cleanup`
removes the runtime partition and reconfigures after each test, which
re-reads slurm.conf and restores stock.

Requires `EnforcePartLimits=ANY` (or YES) in `slurm.conf`: the submit-time
AllowQOS check in `job_mgr.c` is gated by that parameter and is skipped when
it is unset.

## REST partition-config is version-gated

`POST /partitions/` (AllowQOS / TRESBillingWeights pushes) and
`DELETE /partition/{name}` are **only exposed by v0.0.45 (26.05.x)**. v0.0.44
(25.11.x) exposes only `GET /partitions/`. Tests that push partition config at
runtime (access control, billing weights) are gated via the version helper
`require_version(stack, ">=26.05.4")` in `slurm/conftest.py` and skip on the
other versions; import of partition `qos.allowed`/`qos.assigned`/
`nodes.configured` from GET works on both versions.

## Generic cleanup: `reset_slurm_stack`

Every e2e test shares one session-scoped stock stack per version, so a
failing test must never leak state into the next one. The autouse
`slurm_cleanup` fixture calls `reset_slurm_stack(stack, client)` at teardown:

1. **Kill running/pending jobs** (`scancel $(squeue -h -o '%i' | tr '\n' ' ')`,
   no `--all`), waiting until `squeue` is empty so the DB restore cannot
   orphan an in-flight job.
2. **Restore `slurm_acct_db`** from a `mariadb-dump` captured at stack
   startup (`/tmp/origin-db.sql` in the mysql container). This wipes
   associations/users/QOS and clears job accounting (`sacct` empty).
3. **Restart slurmdbd** so its in-memory assoc cache reloads from the restored
   DB. Probe-verified that none of the `sacctmgr` cache refreshes
   (load/dump/clear/reconfigure) or `kill -HUP` fix it, but a restart does
   (fast, ~1-2s to ready). Without it, the `users_association` add_cond path
   (which requires the account-level parent assoc in that cache) silently
   drops the user.
4. **Reconfigure** slurmctld (`client.reconfigure()`), which re-reads
   slurm.conf and reverts runtime partition changes (AllowQOS, nodes,
   TRESBillingWeights).

Order is fixed: kill → restore → restart → reconfigure. The shared baked-in
users (cgray, ...) are **not** deleted — slurmdbd soft-deletes user records on
REST delete, so the restore-then-recreate path is what keeps re-runs clean.

## `AccountingStorageEnforce`

The `slurm.conf` sets
`AccountingStorageEnforce=associations,limits,qos` so slurmdbd actually
enforces associations/limits — otherwise creates silently no-op and the sync
tests would not exercise real enforcement.
