# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import collections
import warnings
from contextlib import ExitStack, contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.urls import path
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.views.generic import View


class Registry(dict):
    """
    Central registry for registration of functionality. Once a Registry is initialized, keys cannot be added or
    removed (though the value of each key is mutable).
    """

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            raise KeyError(_("Invalid store: {key}").format(key=key))

    def __setitem__(self, key, value):
        raise TypeError(_("Cannot add stores to registry after initialization"))

    def __delitem__(self, key):
        raise TypeError(_("Cannot delete stores from registry"))


# Initialize the global registry
registry = Registry(
    {
        "model_actions": collections.defaultdict(set),
        "model_features": dict(),
        "request_processors": list(),
        "plugins": dict(),
        "tables": collections.defaultdict(dict),
        "views": collections.defaultdict(dict),
        "allocation_extensions": collections.defaultdict(list),
        "billing_sources": dict(),
        "third_party_accounts": dict(),
    }
)


def register_allocation_extension(model, extension=None):
    """
    Register an allocation extension model for a given resource model.

    Can be used as a decorator::

        @register_allocation_extension(StorageResource)
        class StorageQuota(PrimaryModel): ...

    Or as a direct function call::

        register_allocation_extension(StorageResource, StorageQuota)

    Args:
        model: A Django model class for the resource.
        extension: A Django model class for the extension (optional).
            If omitted, the decorator derives it from the decorated class.
    """
    resource_path = model._meta.label_lower

    def _register(cls):
        registry["allocation_extensions"][resource_path].append(extension if extension is not None else cls)
        return cls

    if extension is not None:
        registry["allocation_extensions"][resource_path].append(extension)
        return
    else:
        return _register


def get_allocation_extensions(model_or_path):
    """
    Return a list of extension model classes registered for a resource model.

    Accepts a model class or dotted string path.
    """
    if hasattr(model_or_path, "_meta"):
        path = model_or_path._meta.label_lower
    else:
        path = str(model_or_path)
    return list(registry["allocation_extensions"].get(path, []))


def register_billing_source(scope, model, *, get_billable=None, get_rate_scope=None, get_quantity=None):
    """
    Register a billing source model with ColdFront billing.

    Registration is last-wins: registering the same model again replaces the
    previous entry, so a center plugin can override a built-in source.

    Args:
        scope: The resource model class the Rate's ``scope_object`` GenericFK
            targets (e.g. ``StorageResource``, ``SlurmCluster``, ``SlurmQOS``).
            Used by the Rate form to discover registered sources and by invoice
            generation to resolve rates.
        model: The Django model class for the billing source
            (e.g. ``StorageQuota``, ``SlurmAccount``, ``SlurmQOS``).
        get_billable: Required callable ``(user)`` returning
            a queryset of billable source instances for that user. Must filter by
            user; a source without it raises ImproperlyConfigured.
        get_rate_scope: Required callable ``(source)`` returning the rate scope
            object instance for a source. Must return an instance of ``scope``.
        get_quantity: Required callable ``(source, invoice)`` returning the
            native units to bill for a source (e.g. ``hard_limit_bytes``,
            ``service_units``, or ``1`` for a per-item fixed fee). The
            ``invoice`` supplies the billing period so usage-based sources can
            sum consumed usage within it; grant-based sources may ignore it.

    Raises:
        ValueError: If ``scope`` or ``model`` is not a model class, or a
            provided callback is not callable.
    """
    from django.db import models

    if not isinstance(scope, type) or not issubclass(scope, models.Model):
        raise ValueError(_("Billing source scope must be a model class."))
    if not isinstance(model, type) or not issubclass(model, models.Model):
        raise ValueError(_("Billing source model must be a model class."))

    callbacks = {
        "get_billable": get_billable,
        "get_rate_scope": get_rate_scope,
        "get_quantity": get_quantity,
    }
    for name, cb in callbacks.items():
        if cb is None:
            raise ImproperlyConfigured(
                _("Billing source {model} must implement {name}.").format(model=model._meta.label_lower, name=name)
            )
        if not callable(cb):
            raise ValueError(_("Billing source {name} must be callable.").format(name=name))

    registry["billing_sources"][model._meta.label_lower] = {
        "scope": scope,
        "model": model,
        "get_billable": get_billable,
        "get_rate_scope": get_rate_scope,
        "get_quantity": get_quantity,
    }


def get_billing_source(model_or_path):
    """
    Return the billing source registration for a model class or dotted string
    path, or ``None`` if the model is not a registered billing source.
    """
    if hasattr(model_or_path, "_meta"):
        path = model_or_path._meta.label_lower
    else:
        path = str(model_or_path)
    return registry["billing_sources"].get(path)


def get_billing_sources(scope=None):
    """
    Return the list of registered billing source descriptors, optionally
    filtered to those whose rate scope is the given ``scope`` model class.
    """
    sources = registry["billing_sources"].values()
    if scope is not None:
        sources = [src for src in sources if src["scope"] is scope]
    return list(sources)


def billing_scope_types():
    """
    Return an ObjectType queryset for every model class registered as a
    billing-source rate scope. Empty when no billing sources are registered.

    Rate scope types are the ``scope`` of each registration (the object a
    Rate attaches to), not the billable ``model``.
    """
    from django.db.models import Q

    from coldfront.core.models import ObjectType

    q = Q()
    for src in get_billing_sources():
        scope = src["scope"]
        q |= Q(app_label=scope._meta.app_label, model=scope._meta.model_name)
    return ObjectType.objects.filter(q).order_by("app_label", "model") if q else ObjectType.objects.none()


def register_thirdparty_account(key, *, display_name, link_url, callback_url, unlink_url):
    """
    Register a third-party account provider (e.g. ORCID) for the "link a
    3rd-party account to your user account" flow.

    The account app renders a "Third-Party Accounts" page from these
    registrations; each entry supplies the link-start, OAuth callback, and
    unlink URL names.

    Args:
        key: The provider key. Stored as the ``provider`` value on
            ``account.ThirdPartyAccount`` records.
        display_name: Human-readable label for the tab/button.
        link_url: Fully-qualified URL name for the provider's link-start view.
        callback_url: Fully-qualified URL name for the provider's OAuth callback.
        unlink_url: Fully-qualified URL name for the provider's unlink view.

    Raises:
        ValueError: If ``key`` is invalid, already registered, or a required
            field is missing.
    """
    if not key or not isinstance(key, str):
        raise ValueError(_("Third-party account key must be a non-empty string."))
    if key in registry["third_party_accounts"]:
        raise ValueError(_("Third-party account '{key}' is already registered.").format(key=key))
    if not display_name:
        raise ValueError(_("Third-party account '{key}' must specify a display name.").format(key=key))
    link_urls = [link_url, callback_url, unlink_url]
    if any(link_urls) and not all(link_urls):
        raise ValueError(
            _("Third-party account '{key}' must specify link_url, callback_url and unlink_url.").format(key=key)
        )

    registry["third_party_accounts"][key] = {
        "key": key,
        "display_name": display_name,
        "link_url": link_url,
        "callback_url": callback_url,
        "unlink_url": unlink_url,
    }


def get_thirdparty_accounts():
    """
    Return a list of dicts describing each registered third-party account
    provider. Used by the account app's "Third-Party Accounts" page and nav tab.
    """
    return list(registry["third_party_accounts"].values())


def get_thirdparty_account(key):
    """
    Return the registration metadata for ``key``, or None if unregistered.
    """
    return registry["third_party_accounts"].get(key)


def register_model_feature(name, func=None):
    """
    Register a model feature with its qualifying function.

    The qualifying function must accept a single `model` argument. It will be called to determine whether the given
    model supports the corresponding feature.

    This function can be used directly:

        register_model_feature('my_feature', my_func)

    Or as a decorator:

        @register_model_feature('my_feature')
        def my_func(model):
            ...
    """

    def decorator(f):
        registry["model_features"][name] = f
        return f

    if name in registry["model_features"]:
        raise ValueError(f"A model feature named {name} is already registered.")

    if func is None:
        return decorator
    return decorator(func)


def register_model_view(model, name="", path=None, detail=True, kwargs=None):
    """
    This decorator can be used to "attach" a view to any model in ColdFront. This is typically used to inject
    additional tabs within a model's detail view. For example, to add a custom tab to ColdFront's ras.Allocation model:

        @register_model_view(Allocation, 'myview', path='my-custom-view')
        class MyView(ObjectView):
            ...

    This will automatically create a URL path for MyView at `/ras/allocations/<id>/my-custom-view/` which can be
    resolved using the view name `ras:allocation_myview'.

    Args:
        model: The Django model class with which this view will be associated.
        name: The string used to form the view's name for URL resolution (e.g. via `reverse()`). This will be appended
            to the name of the base view for the model using an underscore. If blank, the model name will be used.
        path: The URL path by which the view can be reached (optional). If not provided, `name` will be used.
        detail: True if the path applied to an individual object; False if it attaches to the base (list) path.
        kwargs: A dictionary of keyword arguments for the view to include when registering its URL path (optional).
    """

    def _wrapper(cls):
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        if model_name not in registry["views"][app_label]:
            registry["views"][app_label][model_name] = []

        registry["views"][app_label][model_name].append(
            {
                "name": name,
                "view": cls,
                "path": path if path is not None else name,
                "detail": detail,
                "kwargs": kwargs or {},
            }
        )

        return cls

    return _wrapper


def get_model_urls(app_label, model_name, detail=True):
    """
    Return a list of URL paths for detail views registered to the given model.

    Args:
        app_label: App/plugin name
        model_name: Model name
        detail: If True (default), return only URL views for an individual object.
            Otherwise, return only list views.
    """
    paths = []

    # Retrieve registered views for this model
    try:
        views = [view for view in registry["views"][app_label][model_name] if view["detail"] == detail]
    except KeyError:
        # No views have been registered for this model
        return []

    for config in views:
        # Import the view class or function
        if type(config["view"]) is str:
            view_ = import_string(config["view"])
        else:
            view_ = config["view"]
        if issubclass(view_, View):
            view_ = view_.as_view()

        # Create a path to the view
        name = f"{model_name}_{config['name']}" if config["name"] else model_name
        url_path = f"{config['path']}/" if config["path"] else ""
        paths.append(path(url_path, view_, name=name, kwargs=config["kwargs"]))

    return paths


def register_request_processor(func):
    """
    Decorator for registering a request processor.
    """
    registry["request_processors"].append(func)

    return func


@contextmanager
def apply_request_processors(request):
    """
    A context manager which applies all registered request processors.
    """
    with ExitStack() as stack:
        for request_processor in registry["request_processors"]:
            try:
                stack.enter_context(request_processor(request))
            except Exception as e:
                warnings.warn(f"Failed to initialize request processor {request_processor.__name__}: {e}")
        yield
