# Billing Plugins

ColdFront's billing app prices allocations from **billing sources**. A billing
source is a model whose instances represent something billable — for example a
`StorageQuota` (billed per TB) or a `SlurmAccount` (billed per SU). The
built-in sources live in the resource apps:

- `storage/billing.py` registers `StorageQuota`, scoped to `StorageResource`,
  billing `hard_limit_bytes`.
- `slurm/billing.py` registers `SlurmAccount` (scoped to `SlurmCluster`) and
  `SlurmQOS`.

A plugin can register its own billing sources — e.g. a custom metering system
— without modifying core ColdFront.

---

## The Registry API

Billing sources are registered with `register_billing_source` from
`coldfront.registry`:

```python
register_billing_source(scope, model, *, get_billable, get_rate_scope, get_quantity)
```

| Argument | Meaning |
|---|---|
| `scope` | The resource model class the `Rate.scope_object` GenericFK targets (e.g. `StorageResource`, `SlurmCluster`, `SlurmQOS`) |
| `model` | The Django model class of the billing source (e.g. `StorageQuota`, `SlurmAccount`) |
| `get_billable` | Required callable `(user)` returning a queryset of billable source instances for a user |
| `get_rate_scope` | Required callable `(source)` returning the rate scope object instance for a source; must return an instance of `scope` |
| `get_quantity` | Required callable `(source)` returning the native units to bill (e.g. `hard_limit_bytes`, `service_units`, or `1` for a per-item fixed fee) |

The `unit`/`unit_format` of a source are **not** registered — the `Rate` is
authoritative for the billing dimension. A rate scoped to the source's `scope`
determines the unit format and per-unit price.

All three callbacks are **required**. Registering a source without one raises
`ImproperlyConfigured` at registration time (fail fast) rather than silently
billing nothing.

### Contract

- `get_billable(user)` — return a queryset of source instances to bill for a
  user (e.g. filter by `allocation__project__owner=user`). Generation calls it
  once per source with the invoice owner. Only return sources that are
  actually billable (e.g. allocations that are `active`).
- `get_rate_scope(source)` — return the resource instance a rate is looked up
  against. If it is not an instance of the declared `scope`, generation raises
  a configuration error rather than billing incorrectly.
- `get_quantity(source)` — return the native units to bill. `None` means the
  quantity is not yet set and produces a flagged invalid line; `0` is skipped.

### Last-wins override

Registration is **last-wins**: registering the same `model` again replaces the
previous entry. A center plugin can therefore override a built-in source (e.g.
to change how storage quantities are measured) by re-registering it.

### Querying sources

```python
from coldfront.registry import get_billing_source, get_billing_sources

# All registered sources
sources = get_billing_sources()

# Only sources whose rate scope is a given model class
storage_sources = get_billing_sources(StorageResource)

# A single source by model class or "app.model" path
src = get_billing_source("storage.storagequota")
```

---

## A Minimal Billing Source: Storage Quota

This is the storage app's built-in registration — a minimal example showing
how `StorageQuota` becomes a billing source for a `StorageResource`, billing
the quota's `hard_limit_bytes`.

```python
# src/coldfront/storage/billing.py
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.registry import register_billing_source
from coldfront.storage.models import StorageQuota, StorageResource


def _storage_quota_billable(user):
    qs = StorageQuota.objects.filter(allocation__status=AllocationStatusChoices.STATUS_ACTIVE)
    if user is not None:
        qs = qs.filter(allocation__project__owner=user)
    return qs


def _storage_quota_rate_scope(source):
    return source.storage


def _storage_quota_quantity(source):
    return source.hard_limit_bytes


register_billing_source(
    StorageResource,  # rate scope: a Rate attaches to a StorageResource
    StorageQuota,  # the billable source model
    get_billable=_storage_quota_billable,
    get_rate_scope=_storage_quota_rate_scope,
    get_quantity=_storage_quota_quantity,
)
```

Walking through the contract against the storage models:

- `get_billable(user)` returns the owner's **active** `StorageQuota`
  instances — filtered by the user's projects
  (`allocation__project__owner`).
- `get_rate_scope(source)` returns `source.storage`, the `StorageResource` the
  quota belongs to. A `Rate` scoped to that resource prices the quota.
- `get_quantity(source)` returns `source.hard_limit_bytes` — the native units
  billed at the rate's per-TB unit.

A plugin that needs different storage metering re-registers `StorageQuota`
with its own callables (registration is last-wins), typically from the
plugin's `ready()`:

```python
# myplugin/__init__.py
from coldfront.plugins import PluginConfig


class MyPluginConfig(PluginConfig):
    name = "myplugin"
    verbose_name = "My Plugin"

    def ready(self):
        super().ready()
        from . import billing  # noqa: F401


config = MyPluginConfig
```

Once registered:

1. A **Rate** scoped to `StorageResource` appears in the rate form and is used
   to price `StorageQuota` instances.
2. Invoice generation calls `get_billable(user=invoice.owner)`, `get_rate_scope`, and
   `get_quantity` once per registered source.
3. The quantity (`hard_limit_bytes`) is billed at the storage resource's
   rate, and the source is skipped if it was already billed in an
   overlapping, non-voided invoice period.

See [Plugin Development](development.md) for the full plugin structure.
