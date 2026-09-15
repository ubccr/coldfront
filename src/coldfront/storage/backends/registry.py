# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

# Registry mapping dotted path -> display name
# Populated at Django startup by StorageConfig.ready()
_BACKEND_REGISTRY: dict[str, str] = {}


def register_backend(dotted_path: str) -> None:
    """Register a storage backend for display in the choices dropdown.

    Args:
        dotted_path: Dotted Python path to a ``StorageBackend`` subclass,
            e.g. ``"coldfront.storage.backends.dummy.DummyBackend"``.
    """

    BackendClass = import_string(dotted_path)
    _BACKEND_REGISTRY[dotted_path] = BackendClass.display_name()
    logger.debug("Registered storage backend: %s -> %s", dotted_path, BackendClass.display_name())


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
