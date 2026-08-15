---
name: add-model
description: Step-by-step guide for adding a new model to ColdFront, including all required components (model, filterset, serializer, views, forms, tables, tests, navigation). Use when the user asks to add a new model or object type to ColdFront.
---

# Adding a New Model to ColdFront

Adding a model requires wiring up ~10 components. Work through them in order — each builds on the previous. If the user hasn't specified which app to place the model in, ask first.

## 0. Before You Start

Decide on:
- **App**: which existing app owns this model (`ras`, `slurm`, `storage`, `core`, `users`, `tenancy`, etc.)
- **Base class**: see the hierarchy below
- **URL slug**: the kebab-case name used in URLs (e.g. `storage-clusters`)
- **Model name**: PascalCase (e.g. `StorageCluster`)
- **Verbose names**: for `Meta.verbose_name` / `verbose_name_plural`
- **Feature mixins**: any extra mixins beyond what the base class provides

### Base Class Hierarchy

| Class | Use when |
|---|---|
| `PrimaryModel` | Most models — has `description`, `tags`, `custom_fields`, changelog |
| `OrganizationalModel` | Organizational containers (roles, types, categories) — adds `name` + `description` |
| `NestedGroupModel` | Hierarchical (MPTT) models — adds `parent` FK, `_depth` |
| `ChangeLoggedModel` | Minimal changelog-only models |

All defined in `src/coldfront/models/base.py`. Feature mixins are in `src/coldfront/models/features.py`.

### Feature Mixins (applied before the base class)

```python
class MyModel(AllocatableResourceMixin, PrimaryModel): ...
```

| Mixin | Purpose |
|---|---|
| `AllocatableResourceMixin` | Resource appears in home page "Available Resources" section |
| `CloningMixin` | Adds `clone()` method; define `clone_fields` tuple |
| `CommentingMixin` | Threaded comment support |
| `CustomLinksMixin` | Custom navigation link support |

`TagsMixin` and `CustomFieldsMixin` are included automatically by `PrimaryModel`/`OrganizationalModel`/`NestedGroupModel`.

Additionally, `src/coldfront/ras/models/mixins.py` provides **`AllocationExtensionMixin`** for models extending allocations (used by `SlurmAssociation`, `StorageQuota`).

## 1. Define the Model

**File:** `src/coldfront/<app>/models.py` (or `src/coldfront/<app>/models/<module>.py` for apps with a models package)

```python
from django.db import models
from django.utils.translation import gettext_lazy as _

from coldfront.models import PrimaryModel
from coldfront.models.features import AllocatableResourceMixin


class MyModel(AllocatableResourceMixin, PrimaryModel):
    name = models.CharField(
        verbose_name=_("name"),
        max_length=100,
    )
    some_fk = models.ForeignKey(
        to="app.RelatedModel",
        on_delete=models.PROTECT,
        related_name="my_models",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(  # only if multi-tenant support is needed
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="my_models",
        blank=True,
        null=True,
    )

    clone_fields = ("name",)

    class Meta:
        ordering = ["name"]
        verbose_name = _("my model")
        verbose_name_plural = _("my models")

    def __str__(self):
        return self.name
```

- Add the model to `__all__` in the models module's `__init__.py` if using a package.
- Use `models.PROTECT` for FK `on_delete` unless cascade deletion is explicitly desired.
- `PrimaryModel` already provides `description`, `tags`, `custom_fields`, changelog — don't redeclare them.
- Override `_get_profile()` if using `AllocatableResourceMixin` without a schema; return `None`.
- Use `UniqueConstraint` in `Meta.constraints` for multi-field uniqueness.

## 2. Define Field Choices (if needed)

**File:** `src/coldfront/<app>/choices.py` (or `src/coldfront/choices.py` for shared choices)

```python
from coldfront.choices import ChoiceSet


class MyModelStatusChoices(ChoiceSet):
    STATUS_ACTIVE = "active"
    STATUS_PLANNED = "planned"

    CHOICES = [
        (STATUS_ACTIVE, _("Active"), "green"),
        (STATUS_PLANNED, _("Planned"), "cyan"),
    ]
```

Reference with `choices=MyModelStatusChoices` on the model field and `choices=MyModelStatusChoices.CHOICES` in forms.

## 3. Create the FilterSet

**File:** `src/coldfront/<app>/filtersets.py`

```python
import django_filters
from coldfront.views.filtersets import PrimaryModelFilterSet


class MyModelFilterSet(PrimaryModelFilterSet):
    some_fk = django_filters.ModelMultipleChoiceFilter(
        field_name="some_fk__name",
        queryset=RelatedModel.objects.all(),
        to_field_name="name",
        label=_("Related model (name)"),
    )
    some_fk_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RelatedModel.objects.all(),
        label=_("Related model (ID)"),
    )

    class Meta:
        model = MyModel
        fields = ("id", "name", "description")
```

- Add both `<field>` (name lookup) and `<field>_id` (PK lookup) for every FK.
- Match the base class: `PrimaryModelFilterSet`, `OrganizationalModelFilterSet`, `NestedGroupModelFilterSet`, or `ChangeLoggedModelFilterSet` (all in `src/coldfront/views/filtersets.py`).
- For tenancy: use `TenancyFilterSet` from `src/coldfront/tenancy/filtersets.py` as a mixin.

## 4. Create Forms

### Model Form

**File:** `src/coldfront/<app>/forms/model_forms.py`

```python
from coldfront.forms import PrimaryModelForm


class MyModelForm(PrimaryModelForm):
    class Meta:
        model = MyModel
        fields = ["name", "some_fk", "description", "tags"]
```

### Filter Form

**File:** `src/coldfront/<app>/forms/filterset_forms.py`

```python
from coldfront.forms import PrimaryModelFilterForm


class MyModelFilterForm(PrimaryModelFilterForm):
    model = MyModel
    fieldsets = ("name", "some_fk_id", "description")
    some_fk_id = DynamicModelMultipleChoiceField(
        queryset=RelatedModel.objects.all(),
        required=False,
        label=_("Related Model"),
    )
```

### Bulk Import Form

**File:** `src/coldfront/<app>/forms/model_forms.py` (or a separate import module)

```python
from coldfront.forms import PrimaryModelImportForm
from coldfront.forms.fields.csv import CSVModelChoiceField


class MyModelImportForm(PrimaryModelImportForm):
    some_fk = CSVModelChoiceField(
        queryset=RelatedModel.objects.all(),
        to_field_name="name",
        required=False,
    )

    class Meta:
        model = MyModel
        fields = ["name", "some_fk", "description", "tags"]
```

**Tenancy forms:** If the model has a `tenant` FK, use `TenancyForm` (regular form) and `TenancyImportForm` (import form) as mixins. See `src/coldfront/tenancy/forms/` and examples in `src/coldfront/ras/forms/resources.py` or `src/coldfront/slurm/forms/model_forms.py`.

**Bulk edit forms:** Follow the same pattern with `PrimaryModelBulkEditForm` (see `src/coldfront/forms/bulk_edit.py`).

Export each new form from `src/coldfront/<app>/forms/__init__.py`.

## 5. Create the Table

**File:** `src/coldfront/<app>/tables.py`

```python
from coldfront.tables import PrimaryModelTable
from coldfront.tenancy.tables.columns import TenancyColumnsMixin  # only if model has tenant FK


class MyModelTable(PrimaryModelTable):
    model = MyModel
    fields = ("pk", "name", "some_fk", "description", "tags")
    default_columns = ("pk", "name", "some_fk", "description")
```

- For models with a `tenant` FK, mix in `TenancyColumnsMixin` from `src/coldfront/tenancy/tables/columns.py`.
- Match the base class: `PrimaryModelTable`, `OrganizationalModelTable`, `NestedGroupModelTable`, `ChangeLoggedModelTable`.

## 6. Add Views

**File:** `src/coldfront/<app>/views.py` (or `src/coldfront/<app>/views/<module>.py`)

```python
from coldfront.registry import register_model_view
from coldfront.views.generic import ObjectView, ObjectEditView, ObjectDeleteView, ObjectListView


@register_model_view(MyModel, "list", path="", detail=False)
class MyModelListView(ObjectListView):
    queryset = MyModel.objects.all()
    table = MyModelTable
    filterset = MyModelFilterSet


@register_model_view(MyModel)
class MyModelView(ObjectView):
    queryset = MyModel.objects.all()
    template_name = "<app>/my_model.html"


@register_model_view(MyModel, "add", detail=False)
@register_model_view(MyModel, "edit")
class MyModelEditView(ObjectEditView):
    queryset = MyModel.objects.all()
    form = MyModelForm


@register_model_view(MyModel, "delete")
class MyModelDeleteView(ObjectDeleteView):
    queryset = MyModel.objects.all()


@register_model_view(MyModel, "bulk_import", path="import", detail=False)
class MyModelBulkImportView(ObjectBulkImportView):
    queryset = MyModel.objects.all()
    model_form = MyModelImportForm


@register_model_view(MyModel, "bulk_edit", path="edit", detail=False)
class MyModelBulkEditView(ObjectBulkEditView):
    queryset = MyModel.objects.all()
    table = MyModelTable
    form = MyModelBulkEditForm


@register_model_view(MyModel, "bulk_delete", path="delete", detail=False)
class MyModelBulkDeleteView(ObjectBulkDeleteView):
    queryset = MyModel.objects.all()
    table = MyModelTable
```

- The `@register_model_view` decorator attaches the view to the model's URL namespace. For detail views, omit `detail=False` (defaults to True). For list/add views, pass `detail=False` and provide a `path`.
- `path="import"`/`"edit"`/`"delete"` keep URLs short.
- For FSM workflow views, use `ObjectFlowView` instead (see `src/coldfront/ras/views/allocations.py`).

## 7. Add URL Routes

**File:** `src/coldfront/<app>/urls.py`

```python
from django.urls import path

app_name = "<app>"

urlpatterns = []
```

**Note:** Most view routing is handled by the generic views module (`src/coldfront/views/generic/__init__.py`). URL patterns are only needed for custom views not registered via `@register_model_view`. The registry handles URL dispatch automatically.

**API URLs** — `src/coldfront/<app>/api/urls.py`:

```python
from rest_framework.routers import DefaultRouter
from .views import MyModelViewSet

router = DefaultRouter()
router.register("my-models", MyModelViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
app_name = "<app>-api"
```

## 8. REST API

### Serializer

**File:** `src/coldfront/<app>/api/serializers/<model>.py`

```python
from coldfront.api.serializers import PrimaryModelSerializer
from .nested import NestedRelatedModelSerializer


class MyModelSerializer(PrimaryModelSerializer):
    some_fk = NestedRelatedModelSerializer(nested=True, required=False, allow_null=True, default=None)

    class Meta:
        model = MyModel
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "name",
            "some_fk",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "name", "description")
```

- Use a single FK field with `nested=True` — no separate `_id` companion.
- Match the base class: `PrimaryModelSerializer`, `OrganizationalModelSerializer`, `NestedGroupModelSerializer`, `ChangeLoggedModelSerializer`.
- For tenancy: use `TenantSerializer(nested=True)` from `src/coldfront/tenancy/api/serializers/tenants.py`.

### Nested Serializer

**File:** `src/coldfront/<app>/api/serializers/nested.py`

```python
from coldfront.api.serializers import WritableNestedSerializer


class NestedMyModelSerializer(WritableNestedSerializer):
    class Meta:
        model = models.MyModel
        fields = ["id", "url", "display_url", "display", "name"]
        brief_fields = ("id", "url", "display", "name")
```

**Critical:** Every nested serializer **must** define `brief_fields`. Without it, `get_prefetches_for_serializer()` in `src/coldfront/api/utils.py` raises `AttributeError`, which cascades to `KeyError: 'request'`. Also, the nested serializer's `Meta.model` must match the FK target model, not the source model.

### ViewSet

**File:** `src/coldfront/<app>/api/views.py`

```python
from coldfront.api.viewsets import ColdFrontModelViewSet


class MyModelViewSet(ColdFrontModelViewSet):
    model = MyModel
    serializer_class = MyModelSerializer
    queryset = MyModel.objects.all()
```

Skip `prefetch_related()` — `ColdFrontModelViewSet` resolves prefetches dynamically based on the serializer.

## 9. Add Navigation Menu Entry

**File:** `src/coldfront/navigation/menu.py`

Find the relevant `MenuGroup` and add:

```python
(get_model_item("<app>", "mymodel", _("My Models")),)
```

The model name must be lowercase (not the URL slug). This auto-links to the list view.

If creating a new menu group, define it in the appropriate `Menu` (ALLOCATIONS_MENU, RESOURCES_MENU, ORGANIZATION_MENU, CUSTOMIZATION_MENU, ADMIN_MENU).

## 10. Write Tests

### View Tests

**File:** `tests/<app>/test_views.py`

```python
from coldfront.utils.testing import ViewTestCases


class MyModelTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = MyModel

    @classmethod
    def setUpTestData(cls):
        objects = (
            MyModel(name="Item 1"),
            MyModel(name="Item 2"),
            MyModel(name="Item 3"),
        )
        for obj in objects:
            obj.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Item X",
            "description": "A new item",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,description",
            "Item 4,Fourth item",
            "Item 5,Fifth item",
            "Item 6,Sixth item",
        )
```

- For models with FK fields: `form_data` uses PKs; `csv_data` uses string values matching `to_field_name`.
- For models with `TenancyForm`: `form_data` must include `"tenant_group": None` and `"tenant": None`.

### API Tests

**File:** `tests/<app>/test_api.py`

```python
from coldfront.utils.testing import APIViewTestCases


class MyModelTest(APIViewTestCases.APIViewTestCase):
    model = MyModel
    brief_fields = ["description", "display", "id", "name", "url"]

    @classmethod
    def setUpTestData(cls):
        objects = (
            MyModel(name="Item 1"),
            MyModel(name="Item 2"),
            MyModel(name="Item 3"),
        )
        for obj in objects:
            obj.save()

        cls.create_data = [
            {"name": "Item X", "description": "A new item"},
            {"name": "Item Y", "description": "Another item"},
            {"name": "Item Z", "description": "Third item"},
        ]
```

- For models with FK fields: pre-create FK targets in `setUpTestData` and include their PKs in `create_data`.

### Running Tests

```bash
COLDFRONT_ENV=.env.testing uv run -m pytest tests/<app>/
```

## Common Gotchas

- **`register_models()` is mandatory.** `AppConfig.ready()` must call `register_models(*self.get_models())`. Without it: no changelog views, no object types, broken URLs (`NoReverseMatch`).
- **CSV import uses `to_field_name` values, not PKs.** `CSVModelChoiceField(to_field_name="name")` looks up by name string. CSV test data must use the name string, not the numeric PK.
- **Detail templates are required for view tests.** Missing detail template triggers Django's error handler. Create at minimum `<app>/base.html` and `<app>/<model>.html`.
- **FK filters need explicit `_id` variants** in FilterSets. `Meta.fields` does not auto-generate them.
- **Do NOT run `makemigrations` yourself.** Tell the user to run `uv run coldfront makemigrations` when finished.
- **`PrimaryModel` already provides `description`, `tags`, `custom_fields`.** Don't redeclare them.
- **Serializer FK fields:** Write a single field with `nested=True` — no separate `_id` companion.
- **Custom Group model:** Use `from coldfront.users.models import Group`, not Django's `django.contrib.auth.models.Group`.

## References

- Model base classes: `src/coldfront/models/base.py`, `src/coldfront/models/features.py`
- Example models: `src/coldfront/slurm/models.py`, `src/coldfront/storage/models.py`, `src/coldfront/ras/models/resources.py`
- Navigation menu: `src/coldfront/navigation/menu.py`
- API viewsets: `src/coldfront/api/viewsets/base.py`
- Generic views: `src/coldfront/views/generic/`
- Forms: `src/coldfront/forms/`
- Tables: `src/coldfront/tables/`
- Filtersets: `src/coldfront/views/filtersets.py`
- Tenancy patterns: `src/coldfront/tenancy/forms/`, `src/coldfront/tenancy/tables/columns.py`, `src/coldfront/tenancy/filtersets.py`, `src/coldfront/tenancy/api/serializers/tenants.py`
- Tests: `src/coldfront/utils/testing/` (ViewTestCases, APIViewTestCases)
