# ColdFront - Resource Allocation System

## Repository Summary

ColdFront is an open-source **resource and allocation management system** for high-performance computing (HPC) centers. It provides a central portal for administration, reporting, and measuring the scientific impact of cyberinfrastructure resources. Written in Python (Django), released under Apache 2.0.

---

## Architecture Overview

### Tech Stack
- **Language:** Python 3.12+
- **Framework:** Django 6.x (with django-vite, django-cotton, django-tables2, django-viewflow, django-filter, etc.)
- **Database:** SQLite/MySQL/PostgreSQL (via django-environ)
- **Frontend:** Django templates with HTMX, django-vite, Bootstrap 5 (via django-crispy-forms & crispy-bootstrap5)
- **REST API:** Django REST Framework with drf-spectacular (OpenAPI/Swagger)
- **Task Queue:** django-rq + django-tasks (DB-backed by default, Redis-backed optional)
- **Workflow Engine:** django-viewflow (FSM-based status workflows)
- **Package Manager:** uv (Python >=3.12)
- **Testing:** pytest, coverage, factory-boy
- **Linting:** ruff
- **Template formatting:** djangofmt

### Key Apps

| App | Purpose |
|-----|---------|
| `ras` | Core Resource Allocation System — Resources, ResourceTypes, Projects, ProjectUsers, Allocations, AllocationChangeRequests |
| `slurm` | Slurm integration — Clusters, Partitions, Accounts, Users, Associations, QOS |
| `storage` | Storage integration — Storage Resources, Clusters, Quotas, Snapshot Policies |
| `core` | Foundational models — CustomFields, Tags, ObjectTypes, ChangeLog, Jobs, Notifications, SavedFilters, TableConfigs, CustomLinks, Comments |
| `users` | User/Group management, permissions, API tokens, roles, user preferences |
| `tenancy` | Multi-tenant Tenant/TenantGroup management |
| `account` | User account management (login/logout, proxy UserToken model) |
| `auth` | Authentication backends (LDAP, FreeIPA, mokey, OIDC) |
| `api` | REST API viewsets, serializers, authentication, pagination, renderers |
| `plugins` | Plugin registration, navigation, template extensions, URLs |
| `flows` | Base workflow engine (`ColdFrontFlow`) |
| `forms` | Shared form fields, widgets, layouts, mixins |
| `tables` | Shared table components, columns, pagination |
| `views` | Generic CRUD views, mixins, HTMX views, object actions |

### Base Models & Feature Mixins

All models ultimately derive from `BaseModel` in `src/coldfront/models/base.py`. The hierarchy:

```
BaseModel (RestrictedQuerySet, GenericFK validation)
  ├── ChangeLoggedModel (ChangeLoggingMixin + BaseModel)
  └── ColdFrontModel (ColdFrontFeatureSet + BaseModel)
       ├── PrimaryModel (adds description field)
       ├── OrganizationalModel (adds name + description fields)
       └── NestedGroupModel (MPTTModel for hierarchies)
```

Models can opt into features via mixins defined in `src/coldfront/models/features.py`:

| Mixin | Purpose |
|-------|---------|
| `ChangeLoggingMixin` | Auto `created`/`last_updated` fields, change log snapshots |
| `CloningMixin` | `clone()` method for duplicating objects |
| `TagsMixin` | django-taggit tagging support |
| `CustomFieldsMixin` | JSON-based custom field data storage with validation |
| `CommentingMixin` | Threaded comment support |
| `CustomLinksMixin` | Custom navigation link support |
| `AllocatableResourceMixin` | Resources that can be allocated (`allocatable` method) |

Additionally, `src/coldfront/ras/models/mixins.py` provides **`AllocationExtensionMixin`** for models extending allocations (used by `SlurmAssociation`, `StorageQuota`).

Mixins are applied before the base class, e.g., `class Resource(AllocatableResourceMixin, NestedGroupModel)`.

### Supporting Models (in `core`)

Key utility models defined in `src/coldfront/core/models/`:

- **CustomField** — Type-safe custom fields (text, integer, boolean, date, select, object reference, etc.)
- **CustomFieldChoiceSet** — Reusable choice sets for select/multiselect fields
- **Tag/TaggedItem** — Tagging via django-taggit
- **ObjectType** — Wraps Django ContentType with feature tracking and public/private flags
- **ObjectChange** — Change logging/audit trail
- **Job** — Task/job queue records (used by ColdFrontBackend)
- **SavedFilter** — Saved filter configurations
- **TableConfig** — Per-user table column configuration
- **CustomLink** — Custom navigation links on object detail pages
- **CommentEntry** — Threaded comments on objects

---

## Build and test commands

### CI Checks (run before submitting)

```bash
# Lint violations
uv run ruff check

# Python formatting
uv run ruff format --check

# Django template formatting
uv run djangofmt src/coldfront/

# Frontend TypeScript (ESLint & Prettier)
npm --prefix src/coldfront/static run check

# License compliance
uv run reuse lint

# Pending migrations
uv run coldfront makemigrations --check
```

### Auto-fix and format

```bash
uv run ruff check --fix
uv run ruff format
uv run djangofmt src/coldfront/
```

### Testing

```bash
# Full test suite
COLDFRONT_ENV=.env.testing uv run -m pytest

# Single test file
COLDFRONT_ENV=.env.testing uv run -m pytest tests/<app>/test_views.py

# With coverage
COLDFRONT_ENV=.env.testing uv run -m coverage run -m pytest
```

### Development Setup

```bash
git clone https://github.com/coldfront/coldfront.git
cd coldfront
uv sync --group docs --group dev --extra initializer
DEBUG=True uv run coldfront initial_setup
DEBUG=True PLUGINS="coldfront_initializer" uv run coldfront load_test_data
DEBUG=True uv run coldfront runserver
```

---

## Creating a New ColdFront App

Each app follows a standard structure. See `src/coldfront/slurm/` or `src/coldfront/storage/` as reference implementations.

### Required files

```
src/coldfront/<app>/
├── __init__.py
├── apps.py                  # Must call register_models() in ready()
├── models.py                # Model definitions
├── views.py                 # CRUD views with @register_model_view decorator
├── forms/__init__.py
├── forms/model_forms.py     # Model forms + import forms
├── forms/filterset_forms.py # Filter forms for list views
├── tables.py                # django-tables2 tables
├── filtersets.py            # django-filter filter sets
├── urls.py                  # URL routing
├── api/__init__.py
├── api/serializers/__init__.py
├── api/serializers/<model>.py  # DRF serializers
├── api/serializers/nested.py    # Nested serializers for FK fields
├── api/urls.py               # API URL routing
├── api/views.py              # DRF viewsets
```

### Registration

- Add app to `INSTALLED_APPS` in `src/coldfront/config/base.py`
- Add app URLs to `urlpatterns` in `src/coldfront/config/urls.py`
- Add navigation menu items in `src/coldfront/navigation/menu.py`
- Add API URL patterns in `src/coldfront/config/urls.py`

### Templates

> **Important:** ALL templates live under `src/coldfront/templates/` — never inside the
> app package itself (e.g. `src/coldfront/<app>/templates/`). Django's global
> `TEMPLATES["DIRS"]` includes `src/coldfront/templates`, so templates placed under
> `src/coldfront/templates/<app>/` are resolved automatically; the app does not need
> its own `templates` directory.

- `src/coldfront/templates/<app>/base.html` — extends `generic/base.html`
- `src/coldfront/templates/<app>/<model>.html` — detail view template

### Tests

```
tests/<app>/
├── __init__.py
├── test_views.py            # ViewTestCases.PrimaryObjectViewTestCase
├── test_api.py              # APIViewTestCases.APIViewTestCase
├── test_filtersets.py       # Filter set tests
├── test_tables.py           # Table tests
├── test_forms.py            # Form tests
```

---

## Common Pitfalls

1. **`register_models()` is mandatory.** `AppConfig.ready()` must call `register_models(*self.get_models())`. Without it, models aren't registered with the feature system — no changelog views, no object types, broken URLs (`NoReverseMatch`).

2. **Nested serializers must have `brief_fields` in Meta.** `get_prefetches_for_serializer()` in `src/coldfront/api/utils.py` accesses `Meta.brief_fields` when `nested=True`.

3. **CSV import data uses `to_field_name` values, not PKs.** `CSVModelChoiceField(to_field_name="name")` looks up by name string, not PK. Use `"Test Cluster"` not `"1"`.

4. **Detail templates are required for view tests.** Missing detail template causes Django's 500 error handler to render. Create at minimum `<app>/base.html` and `<app>/<model>.html`.

5. **API tests for models with FK fields need `create_data` with correct FK PKs.** Pre-create related objects in `setUpTestData` and use their PKs.

---

## Key Patterns

### Tenancy Support

When a model needs `tenant` and `tenant_group` fields:

- **Model:** Add `ForeignKey` to `tenancy.Tenant` with `blank=True, null=True`
- **Forms:** Use `TenancyForm` mixin (regular forms) and `TenancyImportForm` mixin (import forms) from `src/coldfront/tenancy/forms/`
- **Tables:** Use `TenancyColumnsMixin` from `src/coldfront/tenancy/tables/columns.py`
- **Filtersets:** Use `TenancyFilterSet` from `src/coldfront/tenancy/filtersets.py`
- **API:** Use `TenantSerializer(nested=True)` from `src/coldfront/tenancy/api/serializers/tenants.py`
- **Tests:** `form_data` must include `"tenant_group": None` and `"tenant": None`

### FSM Workflows

Status workflows use django-viewflow. Define flows in `src/coldfront/<app>/flows/`:
- Allocation flow: `src/coldfront/ras/flows/allocations.py`
- Change request flow: `src/coldfront/ras/flows/change_requests.py`
- Base workflow class: `src/coldfront/flows/base.py` (`ColdFrontFlow`)

### API Serializers

- Base serializers: `src/coldfront/api/serializers/base.py` (`PrimaryModelSerializer`)
- Nested serializers: Must include `brief_fields` in `Meta`
- API viewsets: `src/coldfront/api/viewsets/base.py` (`ColdFrontModelViewSet`)

### Plugin System

Plugins use `PluginConfig` (subclass of Django `AppConfig`). Register via `src/coldfront/plugins/registration.py`. Plugins can register:
- Models, menu items, template extensions, URLs, API endpoints
- Version compatibility checks (`min_version`/`max_version`)
- Example: `coldfront-initializer` for test data loading

### Generic Views

CRUD views use the generic view pattern from `src/coldfront/views/generic/`:
- `ObjectView`, `ObjectEditView`, `ObjectDeleteView`, `ObjectListView`
- `ObjectFlowView` — FSM action views
- `BulkDeleteView`, `BulkImportView`, `BulkEditView`
- Use `@register_model_view` decorator from `src/coldfront/registry.py`

### Custom Group Model

ColdFront uses its own `Group` model at `coldfront.users.models.Group`, **not** Django's `django.contrib.auth.models.Group`. Always reference `from coldfront.users.models import Group` when adding FK relationships to groups.

### Configuration

- Split settings: `src/coldfront/config/settings.py` includes `base.py`, `database.py`, `auth.py`, `logging.py`, `core.py`, `email.py`, `slurm.py`, `plugins.py`
- Environment-driven via django-environ (`.env` files)
- Local overrides: `local_settings.py`, `/etc/coldfront/local_settings.py`
- URL overrides: `local_urls.py`

### Navigation/Menus

Menus are defined in `src/coldfront/navigation/menu.py`. Each app registers menu items via `get_model_item()`. Plugin menus are registered dynamically via `registry["plugins"]["menus"]`.

### License Headers

Every file must include an SPDX license header:
```python
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0
```

---

## Current Version

`src/coldfront/__init__.py`: `__version__ = "2.0.0"` (development branch, pre-production)
