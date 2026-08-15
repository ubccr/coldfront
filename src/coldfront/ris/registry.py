# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Provider registry for the Research Information System (ris) app.

A minimal mapping between a research model (``Publication``/``Funding``) and
the provider classes that serve it. Providers subclass
``ResearchWorkProviderClient`` and register themselves for one or more models
via the ``register_research_work_provider`` decorator.

This is intentionally a module-level registry rather than the global
``coldfront.registry`` store: the global ``Registry`` forbids adding new stores
after initialization, and ris owns this registry as its own seam for
research-work providers.
"""

import collections

from django.utils.translation import gettext as _

from coldfront.ris.providers.base import ResearchWorkProviderClient

__all__ = (
    "get_providers_for_model",
    "register_research_work_provider",
)

# Maps a model class to the provider classes that serve it, in registration
# order.
PROVIDER_REGISTRY = collections.defaultdict(list)


def register_research_work_provider(model):
    """
    Register a research-work provider class (subclass of
    ``ResearchWorkProviderClient``) for one or more models.

    Can be used as a decorator::

        @register_research_work_provider(Funding)
        class NSFClient(ResearchWorkProviderClient): ...

    Or stacked to serve several models::

        @register_research_work_provider(Publication)
        @register_research_work_provider(Funding)
        class ORCIDClient(ResearchWorkProviderClient): ...

    ``model`` may be a single model class or an iterable of model classes.

    The provider must set a non-empty ``key`` and implement ``display_name()``
    (a classmethod); the registry stores only the provider class, nothing else.
    """

    def _register(cls):
        if not (isinstance(cls, type) and issubclass(cls, ResearchWorkProviderClient)):
            raise ValueError(
                _("{class_name} must subclass ResearchWorkProviderClient").format(
                    class_name=getattr(cls, "__name__", cls)
                )
            )
        if not cls.key:
            raise ValueError(_("{class_name} must set a non-empty key").format(class_name=cls.__name__))
        if cls.display_name.__qualname__ == ResearchWorkProviderClient.display_name.__qualname__:
            raise ValueError(_("{class_name} must implement display_name()").format(class_name=cls.__name__))

        if isinstance(model, (list, tuple, set)):
            models = set(model)
        else:
            models = {model}

        for model_ in models:
            PROVIDER_REGISTRY[model_].append(cls)
        return cls

    return _register


def get_providers_for_model(model):
    """
    Return the provider classes registered for ``model`` (in registration
    order). Used by the add/link views to drive search.
    """
    return list(PROVIDER_REGISTRY[model])
