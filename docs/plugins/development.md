# Plugin Development

This guide describes how to develop a plugin for ColdFront. Plugins are
packaged Django apps that follow a specific structure. Refer to the
`tests/dummy_plugin` directory for a complete working example.

## Plugin Structure

A plugin must have this minimum structure:

```
myplugin/
├── __init__.py            # PluginConfig definition
├── models.py              # Data models
├── views.py               # View definitions
├── urls.py                # URL routing
├── navigation.py          # Navigation menu items (optional)
├── template_content.py    # Template extensions (optional)
├── middleware.py          # Custom middleware (optional)
├── tables.py              # Custom table columns (optional)
├── api/
│   ├── __init__.py
│   ├── views.py           # REST API viewsets
│   ├── serializers.py     # REST API serializers
│   └── urls.py            # API URL routing
└── migrations/
    └── __init__.py
```

## PluginConfig

Every plugin must define a `PluginConfig` subclass and expose it as a
`config` variable in `__init__.py`. The PluginConfig defines the plugin's
metadata, version compatibility, and resources.

```python
# myplugin/__init__.py
from coldfront.plugins import PluginConfig


class MyPluginConfig(PluginConfig):
    name = "myplugin"
    verbose_name = "My Plugin"
    version = "1.0"
    description = "A custom ColdFront plugin"
    base_url = "my-plugin"
    min_version = "2.0"
    max_version = "9.0"
    middleware = ["myplugin.middleware.MyMiddleware"]

    def ready(self):
        super().ready()
        # Register custom tables or other resources
        from . import tables  # noqa: F401


config = MyPluginConfig
```

### PluginConfig Attributes

| Attribute | Required | Description |
|---|---|---|
| `name` | Yes | Python module path for the plugin |
| `verbose_name` | Yes | Human-readable name displayed in the UI |
| `version` | Yes | Plugin version string |
| `description` | No | Plugin description |
| `base_url` | No | Root URL path under `/plugins`. Uses plugin label if not set |
| `min_version` | No | Minimum compatible ColdFront version |
| `max_version` | No | Maximum compatible ColdFront version |
| `default_settings` | No | Default configuration parameters |
| `required_settings` | No | Required configuration parameters |
| `middleware` | No | List of middleware classes |
| `django_apps` | No | Additional Django apps to load |
| `author` | No | Plugin author name |
| `author_email` | No | Plugin author email |

## Models

A plugin can define its own data models. Models can inherit from
ColdFront base models to get features like change logging and
permissions.

```python
# myplugin/models.py
from django.db import models
from coldfront.models import ColdFrontModel


class MyModel(ColdFrontModel):
    name = models.CharField(max_length=100)
    number = models.IntegerField(default=100)

    class Meta:
        ordering = ["name"]
```

## Views

Plugins can define views using Django's generic views or ColdFront's
generic object views.

```python
# myplugin/views.py
from django.http import HttpResponse
from django.views.generic import View
from coldfront.views import generic
from coldfront.registry import register_model_view
from .models import MyModel


class MyModelListView(View):
    def get(self, request):
        count = MyModel.objects.count()
        return HttpResponse(f"Instances: {count}")


class MyModelDetailView(generic.ObjectView):
    queryset = MyModel.objects.all()


# Register a view on an existing core model
@register_model_view(Project, "extra", path="other-stuff")
class ExtraProjectView(View):
    def get(self, request, pk):
        return HttpResponse("Success!")
```

## URLs

Plugin URLs are registered under the `/plugins` path. Use the
`plugins:plugin_name` namespace when defining URL names.

```python
# myplugin/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("models/", views.MyModelListView.as_view(), name="my_model_list"),
    path("models/<int:pk>/", views.MyModelDetailView.as_view(), name="my_model"),
]
```

## Navigation Menu Items

Plugins can register navigation menu items with optional action buttons.

```python
# myplugin/navigation.py
from django.utils.translation import gettext as _
from coldfront.plugins.navigation import PluginMenu, PluginMenuButton, PluginMenuItem

items = (
    PluginMenuItem(
        link="plugins:myplugin:my_model_list",
        link_text="Item 1",
        buttons=(
            PluginMenuButton(
                link="plugins:myplugin:my_model_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:myplugin:my_model_list",
        link_text="Item 2",
    ),
)

menu = PluginMenu(
    label=_("My Plugin"),
    groups=(("Group 1", items),),
)
menu_items = items
```

### PluginMenuItem Attributes

| Attribute | Description |
|---|---|
| `link` | Django reverse URL string for the link |
| `link_text` | Text displayed for the link |
| `auth_required` | If True, user must be authenticated |
| `staff_only` | If True, only staff users can see the link |
| `permissions` | List of required permissions |
| `buttons` | List of PluginMenuButton instances |

### PluginMenuButton Attributes

| Attribute | Description |
|---|---|
| `link` | Django reverse URL string for the button |
| `title` | Button tooltip text |
| `icon_class` | Icon CSS class (e.g., `mdi mdi-plus-thick`) |
| `color` | Button color from ButtonColorChoices |
| `permissions` | List of required permissions |

## Template Content

Plugins can inject custom HTML into core ColdFront model detail pages.

```python
# myplugin/template_content.py
from coldfront.plugins.templates import PluginTemplateExtension


class GlobalContent(PluginTemplateExtension):
    def head(self):
        return "<!-- Custom head content -->"

    def navbar(self):
        return "Custom navbar content"


class MyModelContent(PluginTemplateExtension):
    models = ["ras.project"]

    def buttons(self):
        return "Custom buttons"

    def left_page(self):
        return "Custom left page content"

    def right_page(self):
        return "Custom right page content"

    def full_width_page(self):
        return "Custom full width content"


template_extensions = [GlobalContent, MyModelContent]
```

### TemplateExtension Methods

| Method | Location | Description |
|---|---|---|
| `head()` | `<head>` tag | Inject JavaScript or CSS resources |
| `navbar()` | Top navigation | Custom navigation content |
| `buttons()` | Detail view buttons | Add buttons to the detail page |
| `alerts()` | Top of detail view | Alert messages |
| `left_page()` | Left side of detail view | Sidebar content |
| `right_page()` | Right side of detail view | Sidebar content |
| `full_width_page()` | Full width of detail view | Full-width content |
| `list_buttons()` | List view buttons | Buttons on list views |

Set `models` to a list of `"app_label.model_name"` strings to restrict
content to specific model types. Leave it as `None` for all models.

## Middleware

Plugins can register custom Django middleware.

```python
# myplugin/middleware.py
class MyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
```

## Custom Table Columns

Plugins can add columns to existing ColdFront tables.

```python
# myplugin/tables.py
import django_tables2 as tables
from coldfront.tables import register_table_column

mycol = tables.Column(
    verbose_name="My column",
    accessor=tables.A("description"),
)

register_table_column(mycol, "my_section", ProjectTable)
```

## REST API

Plugins can provide REST API endpoints using Django REST Framework.

```python
# myplugin/api/serializers.py
from rest_framework.serializers import ModelSerializer
from myplugin.models import MyModel


class MyModelSerializer(ModelSerializer):
    class Meta:
        model = MyModel
        fields = ("id", "name", "number")
```

```python
# myplugin/api/views.py
from rest_framework.viewsets import ModelViewSet
from myplugin.models import MyModel
from .serializers import MyModelSerializer


class MyModelViewSet(ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
```

```python
# myplugin/api/urls.py
from rest_framework import routers
from .views import MyModelViewSet

router = routers.DefaultRouter()
router.register("my-models", MyModelViewSet)
urlpatterns = router.urls
```

## Installing a Plugin

To install your plugin, add it to the `PLUGINS` list in your
`local_settings.py`:

```python
PLUGINS = [
    "myplugin",
]
```

If your plugin requires configuration, define it in `PLUGINS_CONFIG`:

```python
PLUGINS_CONFIG = {
    "myplugin": {
        "MY_SETTING": "value",
    },
}
```

## Version Compatibility

Use `min_version` and `max_version` in your PluginConfig to declare
compatibility with specific ColdFront versions. If a user attempts to
install your plugin on an incompatible version, ColdFront will raise a
warning and skip loading the plugin.

## Example Plugin

A complete working example plugin is available at
`tests/dummy_plugin`. This plugin demonstrates all the features
described in this guide, including models, views, navigation, template
content, middleware, API endpoints, and custom table columns.
