# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Optional

from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

# Registry mapping dotted path -> display name
# Populated at Django startup by StorageConfig.ready()
_BACKEND_REGISTRY: dict[str, str] = {}


def register_backend(dotted_path: str, display_name: Optional[str] = None) -> None:
    """Register a storage backend for display in the choices dropdown.

    Args:
        dotted_path: Dotted Python path to a ``StorageBackend`` subclass,
            e.g. ``"coldfront.storage.backends.dummy.DummyBackend"``.
        display_name: Human-readable name for the dropdown. If ``None``,
            derived from the class name (e.g. ``"Dummy"`` for ``DummyBackend``).
    """
    if display_name is None:
        # Derive display name from the class name by stripping "Backend" suffix
        cls_name = dotted_path.rsplit(".", 1)[-1]
        if cls_name.endswith("Backend"):
            cls_name = cls_name[:-7]
        display_name = cls_name

    _BACKEND_REGISTRY[dotted_path] = display_name
    logger.debug("Registered storage backend: %s -> %s", dotted_path, display_name)


def get_backend_choices() -> list[tuple[str, str]]:
    """Return sorted choices suitable for a ``ChoiceField``.

    Returns:
        List of ``(dotted_path, display_name)`` tuples, sorted by display name.
        The first entry is the null choice (no backend selected).
    """
    choices = [("", "--- No backend ---")]
    choices.extend(
        sorted(
            _BACKEND_REGISTRY.items(),
            key=lambda item: item[1].lower(),
        )
    )
    return choices


def get_backend(dotted_path: str | None, cluster_name: str = "") -> object | None:
    """Import and instantiate a backend by its dotted path.

    Args:
        dotted_path: Dotted Python path to a ``StorageBackend`` subclass,
            or ``None`` for clusters with no backend.
        cluster_name: The cluster name to pass to the backend constructor.

    Returns:
        An instance of the backend class, or ``None`` if ``dotted_path`` is
        ``None``.

    Raises:
        ModuleNotFoundError: If the dotted path cannot be imported.
    """
    if dotted_path is None:
        return None
    BackendClass = import_string(dotted_path)
    return BackendClass(cluster_name=cluster_name)


def discover_backends() -> None:
    """Auto-discover ``StorageBackend`` subclasses in the backends package.

    Scans ``coldfront.storage.backends`` for modules containing
    ``StorageBackend`` subclasses and registers them.  Modules that fail
    to import (e.g., missing optional dependencies) are skipped with a
    warning.
    """
    import importlib
    import pkgutil

    from .base import StorageBackend

    # Get the backends package
    pkg = importlib.import_module("coldfront.storage.backends")

    for importer, modname, _ in pkgutil.iter_modules(
        pkg.__path__,
        prefix="coldfront.storage.backends.",
    ):
        # Skip the base and registry modules
        if modname in (
            "coldfront.storage.backends.base",
            "coldfront.storage.backends.registry",
            "coldfront.storage.backends.__init__",
        ):
            continue

        try:
            mod = importlib.import_module(modname)
        except ImportError as exc:
            logger.warning("Skipping storage backend %s (import error: %s)", modname, exc)
            continue

        # Find StorageBackend subclasses in the module
        for attr_name in dir(mod):
            cls = getattr(mod, attr_name)
            if isinstance(cls, type) and issubclass(cls, StorageBackend) and cls is not StorageBackend:
                dotted_path = f"{modname}.{attr_name}"
                register_backend(dotted_path)
                break  # One backend class per module
